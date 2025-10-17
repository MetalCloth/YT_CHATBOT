from celery import Celery
import fastapi
from requests import Request
import asyncio
from fastapi import FastAPI
import json
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from database.session import create_job,update_job_status,create_table,get_job,engine,AsyncSessionLocal

from workers.task import app,app2

app = Celery(
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
    """This is triggered whenever the redis thingy is changed or mutated or updated"""

    #     "user_id":key,
        # # "message":value.message,
        # "sender":"Human",
        # "full_summary":value.full_summary

    user_id=job['user_id']
    sender=job['sender']
    full_summary=job['full_summary']
    job_info=""
    async with AsyncSessionLocal() as db:
        try:
            job_info=await get_job(db, job_id=user_id)
            print(f"CELERY WORKER: postgres job  '{user_id}' complete.")
            result=""
        # Process using your graph apps
            if full_summary:
                result = await asyncio.to_thread(app2.invoke,{
                    'video_id': job_info['video_id'],
                    'documents': [],
                    'question': '',
                    'answer': ""
                })
                
            else:
                result = await asyncio.to_thread(app.invoke,{
                    'video_id': job_info['video_id'],
                    'documents': [],
                    'question': job_info['question'],
                    'answer': "",
                })

            summary_text = json.dumps(result)
                

            # Update Postgres
            print("JOB INFO IS OR SHOULD ",job_info)
            await update_job_status(db, job_id=job_info['job_id'], status='SUCCESS', summary=summary_text)
            print(f"CELERY WORKER: PostgreSQL update for job '{user_id}' complete.")

            print(f"Job {job_info['video_id']} processed successfully.")
            return {"response": summary_text}

        except Exception as e:
            print(f"Error processing job {job_info['video_id']}: {e}")
            return {"response": f"Error -> {e}"}            
        
@app.task
def process_video_summary(job):
    return asyncio.run(asynchronous_process(job))
# @app.task
# def process_video_summary(r,key):
#     print("CELERY WORKING IS GONNA SHIT")

#     while True:
#         print("RECIEVEING JOB FROM CELRY_APP")
#         job=receive_msg_from_redis(r,key)

#         print("JOB IS FROM CELERY_APP",job)

#         """job={
#             user_id:"1234abshadmm"
#          "full_summary":bool,
#          sender="API"
#         }"""
#         user_id=job['user_id']
#         sender=job['sender']
#         full_summary=job['full_summary']


#         job=asyncio.run(get_postgres_job(job_id=user_id))

#         print("SENDING TO THE FUCKING GRAPH")

#         try:

#             if full_summary:
#                 result=app2.invoke({
#                     'video_id':job['video_id'],
#                     'documents':[],
#                     'question':'',
#                     'answer':""
#                 })
            
#             else:
#                 result=app.invoke({
#                     'video_id':job['video_id'],
#                     'documents':[],
#                     'question':job['question'],
#                     'answer':"",
#                 })

#             print("SENT TO THE FUCKING GRAPH AND NOW RETRIEVED THE ANSWER")
#             update_job_status(job_id=job['video_id'],status='SUCCESS',summary=result)
#             print("SENT TO THE DATABASE PLS SEEE PLSSS job_id",job['video_id'])
#             return {'response':result}
#         except Exception as e:
#             {'response':f"Error has been found refer to this error -> {e}"}


# @app.task
# def process_video_summary(job):
#     """
#     job = {
#         "user_id": str,
#         "full_summary": bool,
#         "sender": str
#     }
#     """
#     user_id = job['user_id']
#     full_summary = job['full_summary']

#     # Fetch job info from Postgres
#     job_info = asyncio.run(get_postgres_job(job_id=user_id))

#     # Process using your graph apps
#     try:
#         if full_summary:
#             result = app2.invoke({
#                 'video_id': job_info['video_id'],
#                 'documents': [],
#                 'question': '',
#                 'answer': ""
#             })
#         else:
#             result = app.invoke({
#                 'video_id': job_info['video_id'],
#                 'documents': [],
#                 'question': job_info['question'],
#                 'answer': "",
#             })

#         # Update Postgres
#         asyncio.run(update_postgres(job_id=job_info['video_id'], status='SUCCESS', summary=result))
#         print(f"Job {job_info['video_id']} processed successfully.")
#         return {"response": result}

#     except Exception as e:
#         print(f"Error processing job {job_info['video_id']}: {e}")
#         return {"response": f"Error -> {e}"}            




        