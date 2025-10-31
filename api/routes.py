""""ERROR MIGHT BE DUE TO UNABILITY TO UPDATE OR DELETE POSTGRESQL"""

import fastapi
from requests import Request

from fastapi import FastAPI,Depends,WebSocket,HTTPException
from ai_core.utils import PreProcessing
import time
import redis.asyncio as aioredis

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from database.session import (
    create_job, update_job_status, create_table, get_job, engine, 
    AsyncSessionLocal, add_chat_message,
)
from database.redis_session import (
    redis, receive_msg_from_redis, msg_to_redis, r, Value,
    add_videos_to_session_redis, get_session_videos_redis
)

import uuid
from typing import Optional, List
from pydantic import BaseModel
import json


api=FastAPI()



class StartChatPayload(BaseModel):
    user_id: str 

class AddVideoPayload(BaseModel):
    video_id: Optional[str] = None
    playlist_id: Optional[str] = None

class AskQuestionPayload(BaseModel):
    question: Optional[str] = None
    full_summary: bool = False


@api.get('/')
def root():
    return {'w':'welcome bhosadiwale'}


async def get_db():
    async with AsyncSessionLocal() as db:
        yield db


@api.get('/health')
def health():
    return {'health':200}



@api.post('/chat/start')
async def start_new_chat(payload: StartChatPayload, db:AsyncSession=Depends(get_db)):
    """
    Creates a new, empty session for a user.
    Returns a new session_id.
    """
    try:
        await create_table() 
        
        session_id = str(uuid.uuid4())

        print(f"THIS MESSAGE IS FROM ROUTES.PY Created new session {session_id} for user {payload.user_id}")

        return {
            "message": "New chat session created",
            "session_id": session_id,
            "user_id": payload.user_id
        }
    except Exception as e:
        print(f"THIS MESSAGE IS FROM ROUTES.PY  Error in /chat/start: {e}")
        raise HTTPException(status_code=500, detail="Could not start chat session.")



@api.post('/chat/{session_id}/add')
async def add_videos_to_chat(session_id: str, payload: AddVideoPayload):
    """
    Adds one or more videos/playlists to session
    """
    try:
        if not payload.video_id and not payload.playlist_id:
            raise HTTPException(status_code=400, detail="You provide a video_id or a playlist_id.")

        video_ids_to_add: List[str] = []

        if payload.playlist_id:
            playlist_url = f"https://www.youtube.com/playlist?list={payload.playlist_id}"
            video_ids_list = PreProcessing.get_playlist_video_ids(playlist_url)
            if not video_ids_list:
                raise HTTPException(status_code=404, detail="Playlist is empty or not found bhangi.")
            video_ids_to_add.extend(video_ids_list)
        
        if payload.video_id:
            if payload.video_id not in video_ids_to_add:
                video_ids_to_add.append(payload.video_id)
        
        if not video_ids_to_add:
            raise HTTPException(status_code=400, detail="No valid videos found to add.")

        add_videos_to_session_redis(r, session_id, video_ids_to_add)

        return {
            "message": f"Added {len(video_ids_to_add)} video(s) to session {session_id}",
            "session_id": session_id,
            "added_videos": video_ids_to_add
        }
    except Exception as e:
        print(f"THIS MESSAGE IS FROM ROUTES.PY  Error in /chat/add: {e}")
        raise HTTPException(status_code=500, detail="Could not add videos to session.")


@api.post('/chat/{session_id}/ask')
async def ask_question(session_id: str, payload: AskQuestionPayload, db:AsyncSession=Depends(get_db)):
    """
    Asks a question (or requests a full_summary) within a "study room".
    This triggers the RAG pipeline.
    """
    try:
        video_ids = get_session_videos_redis(r, session_id)
        if not video_ids:
            raise HTTPException(status_code=404, detail="No videos found in this session. Add videos first using the /add endpoint.")
        
        question_text = payload.question
        if payload.full_summary:
            if payload.question:
                print("WTHIS MESSAGE IS FROM ROUTES.PY  arning: Both question and full_summary=true received. Prioritizing full_summary.")
            question_text = "GENERATE FULL SUMMARY" # Use a consistent internal query
        elif not question_text:
             raise HTTPException(status_code=400, detail="You must provide a 'question' or set 'full_summary' to true.")
        
        await add_chat_message(db, session_id, "human", question_text)

        job_id_key = str(uuid.uuid4())
        
        video_id_string = ",".join(video_ids) 
        ### makes into list seperated by ,
        
        await create_job(db, job_id=job_id_key, video_id=video_id_string, question=question_text)

        msg_to_redis(r, job_id_key, value=Value(
            user_id=job_id_key,        
            session_id=session_id,     
            full_summary=payload.full_summary,
            sender="Human",
        ))

        print(f"THIS MESSAGE IS FROM ROUTES.PY  Sent job {job_id_key} for session {session_id} to Redis")

        return {
            'response': 'Your question is being processed. Connect via WebSocket for the answer.',
            'job_id': job_id_key,
            'session_id': session_id
        }

    except HTTPException as e:
        raise e 
    except Exception as e:
        print(f"THIS MESSAGE IS FROM ROUTES.PY  {e}")
        raise HTTPException(status_code=500, detail="Could not process question.")


# @api.websocket('/ws/status/{job_id}')
# async def websocket_endpoint(websocket:WebSocket,job_id:str):
#     """"Gonna dismantel the redis_listener into splitted personality and not a fucking funcition"""
#     import os
#     await websocket.accept()
#     os.environ['REDIS_API_KEY'] = os.getenv('REDIS_API_KEY')

#     print("STHIS MESSAGE IS FROM ROUTES.PY  ERVER ONLINE")

#     redis_url = f"redis://default:{os.getenv('REDIS_API_KEY')}@redis-12857.c62.us-east-1-4.ec2.redns.redis-cloud.com:12857/0"
#     r = aioredis.from_url(redis_url, decode_responses=True)

#     pubsub = r.pubsub()
#     await pubsub.subscribe('from_redis')

#     print("STHIS MESSAGE IS FROM ROUTES.PY  UBSCRIBED TO REDIS BY API  {job_id}NOW LISTENING")

#     try:
#         async for message in pubsub.listen():
#             if message['type']=='message':
#                 channel=message['channel']
#                 print("CTHIS MESSAGE IS FROM ROUTES.PY  HANNEL NAME IS",channel)
#                 job_data = json.loads(message["data"])

#                 if job_data['user_id']!=job_id:
#                     continue


#                 print("STHIS MESSAGE IS FROM ROUTES.PY  ENDING TO CELERY")
                
                
#                 print(f'THIS MESSAGE IS FROM ROUTES.PY  New message on channel "from redis"')

#                 summary=""
#                 async with AsyncSessionLocal() as db:
#                         job_info = await get_job(db, job_id=job_id)
#                         if job_info:
#                             summary = job_info['response'] 
                    
#                 await r.blpop(job_data['user_id'],timeout=0)

#                 print("GTHIS MESSAGE IS FROM ROUTES.PY  OT THE SUMMMARY BABYYYYYY",summary)
#                 await websocket.send_text(summary)
#                 break

#     except Exception as e:
#         print("ETHIS MESSAGE IS FROM ROUTES.PY  RROR OCCURED IN WEBSOCKET",e)

#     finally:
#         print(f"THIS MESSAGE IS FROM ROUTES.PY  Client  disconnecting.")
#         await pubsub.unsubscribe('from_redis')
#         await r.close()
#         await websocket.close()

# In routes.py

@api.websocket('/ws/status/{job_id}')
async def websocket_endpoint(websocket:WebSocket,job_id:str):
    """"Gonna dismantel the redis_listener into splitted personality and not a fucking funcition"""
    import os
    await websocket.accept()
    os.environ['REDIS_API_KEY'] = os.getenv('REDIS_API_KEY')

    from workers.celery_app import process_video_summary
    print("SERVER ONLINE")

    # --- FIX #1: CHECK FIRST ---
    # Check if the job is *already* done (catches race conditions)
    async with AsyncSessionLocal() as db:
        job_info = await get_job(db, job_id=job_id)
        if job_info and (job_info['status'] == 'SUCCESS' or job_info['status'] == 'FAILED'):
            print(f"Job {job_id} was already completed. Sending result immediately.")
            await websocket.send_text(job_info['response'])
            await websocket.close()
            return # Exit

    # --- IF NOT DONE, THEN LISTEN ---
    redis_url = f"redis://default:{os.getenv('REDIS_API_KEY')}@redis-12857.c62.us-east-1-4.ec2.redns.redis-cloud.com:12857/0"
    r = aioredis.from_url(redis_url, decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe('from_redis')

    print(f"SUBSCRIBED TO REDIS BY API {job_id} NOW LISTENING")

    try:
        async for message in pubsub.listen():
            if message['type']=='message':
                channel=message['channel']
                print("CHANNEL NAME IS",channel)
                job_data = json.loads(message["data"])

                if job_data['user_id'] != job_id:
                    continue
                
                print(f'New message on channel "from redis" for our job_id')

                summary=""
                async with AsyncSessionLocal() as db:
                        job_info = await get_job(db, job_id=job_id)
                        if job_info:
                            summary = job_info['response'] 
                    
                # --- FIX #2: DELETE THE BLOCKING POP ---
                # await r.blpop(job_data['user_id'],timeout=0) # <--- DELETED

                print("GOT THE SUMMMARY BABYYYYYY",summary)
                await websocket.send_text(summary)
                break # We're done, break the loop

    except Exception as e:
        print("ERROR OCCURED IN WEBSOCKET",e)

    finally:
        print(f"Client {job_id} disconnecting.")
        await pubsub.unsubscribe('from_redis')
        await r.close()
        await websocket.close()