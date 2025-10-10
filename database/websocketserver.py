import asyncio
import socketio
import uvicorn
import uuid
from fastapi import FastAPI
from pydantic import BaseModel
import datetime

from workers.task import app, app2

api = FastAPI(title="YouTube Summarizer API")
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
sio_app = socketio.ASGIApp(socketio_server=sio, other_asgi_app=api)

job_to_sid = {}
job_results_cache = {}


class QueryPayload(BaseModel):
    question: str
    full_summary: bool = False

async def long_running_query_task(job_id: str, video_id: str, question: str, full_summary: bool):
    """
    This function performs the actual, potentially long-running summarization work.
    """
    print(f"BACKGROUND: Starting job '{job_id}' for video '{video_id}'.")

    try:
        initial_state = {
            'video_id': video_id,
            'documents': [],
            'question': question,
            'answer': ""
        }

        if full_summary:
            result = await asyncio.to_thread(app2.invoke, initial_state)
        else:
            result = await asyncio.to_thread(app.invoke, initial_state)
        
        final_answer = result.get('answer', 'No answer found in the result state.')

        print(f"BACKGROUND: Finished job '{job_id}'. Result: {str(final_answer)[:100]}...")

        response_payload = {'job_id': job_id, 'status': 'SUCCESS', 'response': final_answer}
        
    except Exception as e:
        print(f"BACKGROUND: An error occurred in job '{job_id}': {e}")
        response_payload = {'job_id': job_id, 'status': 'FAILED', 'error': str(e)}

    sid_for_job = job_to_sid.get(job_id)

    if sid_for_job:
        await sio.emit('job_done', response_payload, to=sid_for_job)
        print(f"SERVER: Pushed result for job '{job_id}' to client {sid_for_job}.")
        del job_to_sid[job_id]
    else:
        print(f"SERVER: No active client for job '{job_id}'. Caching result for polling.")
        job_results_cache[job_id] = response_payload


# --- API Endpoints ---
@api.get('/')
def root():
    return {'message': 'Welcome to the real-time YT Summarizer API.'}

@api.post("/start-query/{video_id}")
async def start_query(video_id: str, payload: QueryPayload):
    job_id = str(uuid.uuid4())
    print(f"SERVER: Received request for video '{video_id}'. Assigned Job ID: {job_id}")
    sio.start_background_task(
        long_running_query_task, 
        job_id, 
        video_id, 
        payload.question, 
        payload.full_summary
    )
    return {"job_id": job_id, "message": "Job started. Use this ID to check status."}

@api.get("/status/{job_id}")
async def get_job_status(job_id: str):
    if job_id in job_results_cache:
        return job_results_cache[job_id]
    
    if job_id in job_to_sid:
        return {"job_id": job_id, "status": "PROCESSING", "message": "Job is currently processing."}
    
    return {"job_id": job_id, "status": "UNKNOWN", "message": "Job not found or has expired from cache."}


@sio.event
async def connect(sid, environ, auth):
    job_id = auth.get('jobId')
    if not job_id:
        print(f"SERVER: Client {sid} connected without a job_id. Disconnecting.")
        await sio.disconnect(sid)
        return

    if job_id in job_results_cache:
        print(f"SERVER: Client {sid} connected for job '{job_id}'. Found cached result, sending immediately.")
        await sio.emit('job_done', job_results_cache[job_id], to=sid)
        del job_results_cache[job_id]
    else:
        print(f"SERVER: Client {sid} connected and is now waiting for job '{job_id}'.")
        job_to_sid[job_id] = sid

@sio.event
async def disconnect(sid):
    print(f"SERVER: Client {sid} disconnected.")
    for job_id, session_id in list(job_to_sid.items()):
        if session_id == sid:
            del job_to_sid[job_id]
            print(f"SERVER: Cleaned up waiting list for job '{job_id}'.")
            break

