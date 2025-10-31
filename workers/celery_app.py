from celery import Celery
import fastapi
from requests import Request
import asyncio
from fastapi import FastAPI
import json
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from database.session import (
    create_job, update_job_status, create_table, get_job, engine, 
    AsyncSessionLocal, DATABASE_URL,
    add_chat_message, get_chat_history
)
from database.redis_session import msg_to_redis, r, Value

from workers.task import qa_app, summary_app


celery_app = Celery(
    "tasks",
    broker="redis://default:98MDP1pPNJTcUmUNTjRvICOtC7VMRopc@redis-12857.c62.us-east-1-4.ec2.redns.redis-cloud.com:12857/0",
    backend="redis://default:98MDP1pPNJTcUmUNTjRvICOtC7VMRopc@redis-12857.c62.us-east-1-4.ec2.redns.redis-cloud.com:12857/0"
)


async def update_postgres(job_id: str, status: str, summary: str):
    async with AsyncSessionLocal() as db:
        await update_job_status(db, job_id=job_id, status=status, summary=summary)
        print(f"CELERY WORKER: PostgreSQL update for job '{job_id}' complete.")


async def get_postgres_job(job_id: str):
    async with AsyncSessionLocal() as db:
        job=await get_job(db, job_id=job_id)
        print(f"CELERY WORKER: postgres job  '{job_id}' complete.")
        return job


async def asynchronous_process(job):
    """
    This is the main "Exam Study Session" worker.
    It fetches all context (videos + chat history) and runs the RAG.
    """
    
    engine=create_async_engine(DATABASE_URL)
    TaskSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    job_id = job['user_id']        
    session_id = job['session_id'] 
    full_summary = job['full_summary']
    playlist_id=job.get('playlist_id')

    job_info = ""
    async with TaskSessionLocal() as db:
        print("THIS MESSAGE IS FROM CELERY.PY GONNA START GETTING POSTGRESQL JOB")
        try:
            job_info = await get_job(db,job_id)
            if not job_info:
                raise Exception(f"No job info found for job_id {job_id}")
                
            question = job_info['question']
            video_id_string = job_info['video_id'] 

            print("GTHIS MESSAGE IS FROM CELERY.PY OT POSTGRES JOB LETS SEE HOW IT GOES")
            chat_history = await get_chat_history(db, session_id=session_id)

            print("GTHIS MESSAGE IS FROM CELERY.PY OT CHATHISTORY LETS SEE HOW IT GOES")

            print(f"THIS MESSAGE IS FROM CELERY.PY Retrieved {len(chat_history)} previous messages.")



            graph_state = {
                'video_id': video_id_string,  
                'playlist_id': None,          
                'session_id': session_id,     
                'chat_history': chat_history, 
                'documents': [],
                'question': question,
                'answer': "",
            }

            print("Running main graph ")
            result = await asyncio.to_thread(qa_app.invoke, graph_state)
            final_answer_text = "Error: Answer not found in result." 
            if isinstance(result, dict):
                final_answer_text = result.get('answer', "Error: 'answer' key missing.")
            else:
                print(f"THIS MESSAGE IS FROM CELERY.PY Warning: Graph invocation returned unexpected type: {type(result)}")
                final_answer_text = str(result) 
            
            if not isinstance(final_answer_text, str):
                 final_answer_text = str(final_answer_text)

            print(f"THIS MESSAGE IS FROM CELERY.PY Final answer generated: {final_answer_text[:50]}...")

            await add_chat_message(db, session_id, "ai", final_answer_text)

            await update_job_status(db, job_id=job_id, status='SUCCESS', summary=final_answer_text)

            print(f"THIS MESSAGE IS FROM CELERY.PY CELERY WORKER: PostgreSQL update for job '{job_id}' complete.")
            
            value = Value(
                user_id=job_id,
                sender="AI",
                session_id=session_id
            )

            msg_to_redis(r, job_id, value, channel='from_redis')

            print(f"THIS MESSAGE IS FROM CELERY.PY --- Job {job_id} Processed Successfully ---")
            return {"response": final_answer_text}

        except Exception as e:

            return {"response": f"Error -> {e}"} 

        finally:
            await engine.dispose()


@celery_app.task
def process_video_summary(job):
    return asyncio.run(asynchronous_process(job))


#  CREATE TABLE IF NOT EXISTS data (
#             id SERIAL PRIMARY KEY,
#             job_id TEXT UNIQUE NOT NULL,
#             video_id TEXT NOT NULL,
#             question TEXT,
#             status TEXT NOT NULL,
#             response TEXT,
#             created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() at time zone 'utc')
#         );

            # if full_summary==True:
            #     graph_state={
            #         'video_id':video_id_string,
            #         'playlist_id':None,
            #         'chat_history':[],
            #         'session_id':session_id,

            #     }
            
            # else:
