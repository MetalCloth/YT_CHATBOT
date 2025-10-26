from celery import Celery
import fastapi
from requests import Request
import asyncio
from fastapi import FastAPI
import json
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from database.session import create_job,update_job_status,create_table,get_job,engine,AsyncSessionLocal,DATABASE_URL

from workers.task import app,app2


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
    from database.redis_session import msg_to_redis,r,Value

    """This is triggered whenever the redis thingy is changed or mutated or updated"""

    #     "user_id":key,
        # # "message":value.message,
        # "sender":"Human",
        # "full_summary":value.full_summary
    engine=create_async_engine(DATABASE_URL)
    TaskSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    user_id=job['user_id']
    sender=job['sender']
    full_summary=job['full_summary']
    playlist_id=job.get('playlist_id')
    job_info=""
    async with TaskSessionLocal() as db:
        try:
            job_info=await get_job(db, job_id=user_id)
            print(f"CELERY WORKER: postgres job  '{user_id}' complete.")
            result=""
        # Process using your graph apps
            if full_summary:
                result = await asyncio.to_thread(app2.invoke,{
                    'video_id': job_info['video_id'],
                    'playlist_id':playlist_id,
                    'documents': [],
                    'question': '',
                    'answer': ""
                })
                
            else:
                result = await asyncio.to_thread(app.invoke,{
                    'video_id': job_info['video_id'],
                    'playlist_id':playlist_id,
                    'documents': [],

                    'question': job_info['question'],
                    'answer': "",
                })
            
            final_answer_text = "Error: Answer not found in result." # Default
            if isinstance(result, dict):
                final_answer_text = result.get('answer', "Error: 'answer' key missing.")
            else:
                print(f"Warning: Graph invocation returned unexpected type: {type(result)}")
                final_answer_text = str(result) # Fallback

            if not isinstance(final_answer_text, str): # Ensure string
                 final_answer_text = str(final_answer_text)

            summary_text = json.dumps(result)

            print("SUMMARY TEXT SHOULD BE",summary_text[:15])
                

            # Update Postgres
            print("JOB INFO IS OR SHOULD ",job_info)
            await update_job_status(db, job_id=job_info['job_id'], status='SUCCESS', summary=final_answer_text)

            print(f"CELERY WORKER: PostgreSQL update for job '{user_id}' complete.")
            """Adding a function to update redis shit tooo"""

        
            value=Value(
                user_id=user_id,
                sender="AI",
            )
            
            

            msg_to_redis(r,user_id,value,channel='from_redis')

            print("SENT NOW THE ANSWER KEY TO THE REDIS TOO")


            print(f"Job {job_info['video_id']} processed successfully.")
            return {"response": final_answer_text}

        except Exception as e:
            print(f"Error processing job {job_info['video_id']}: {e}")
            return {"response": f"Error -> {e}"}     

        finally:
            await engine.dispose()       
        

# """This function will recieve update from redis and will blpop and fetch postgresql and kindly send to api ig"""
# async def redis_celery_postgresql_api(job):
#     engine = create_async_engine(DATABASE_URL)
#     TaskSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
#     user_id=job['user_id']
#     sender=job['sender']
#     full_summary=job['full_summary']
#     job_info=""
#     async with TaskSessionLocal() as db:
#         print("SENDER IS",sender)
#         if sender=="AI":
#             try:
#                 job_info=await get_job(db,job_id=user_id)
#                 print(f"JOB INFO IS {job_info}")

#                 response=job_info['response']

#                 print("RESPONSE IS THIS ",response)

#                 print("SENDING TO THE API BIG BOI")

#                 return response

                

#                 """Send to the fucking API idk how but do it later obv"""


#             except Exception as e:
#                 print("ERROR FACED",e)
#             finally:
#                 await engine.dispose()

# @app.task
# def send_to_hell(job):
#     return asyncio.run(redis_celery_postgresql_api(job))



@celery_app.task
def process_video_summary(job):
    return asyncio.run(asynchronous_process(job))

# @app.task
# def msg_redis_postgresql_api(job):





