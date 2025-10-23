""""ERROR MIGHT BE DUE TO UNABILITY TO UPDATE OR DELETE POSTGRESQL"""

import fastapi
from requests import Request

from fastapi import FastAPI,Depends,WebSocket
from workers.task import app,app2
import time
import redis.asyncio as aioredis

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from database.session import create_job,update_job_status,create_table,get_job,engine,AsyncSessionLocal
import uuid
from typing import Optional
from pydantic import BaseModel
from database.redis_session import redis,receive_msg_from_redis,msg_to_redis,r,Value

import json



api=FastAPI()


class QueryPayload(BaseModel):
    question: Optional[str]
    full_summary: str = False

@api.get('/')
def root():
    return {'w':'welcome bhosadiwale'}


async def get_db():
    async with AsyncSessionLocal() as db:
        yield db


"""THERE IS FRONTEND WHO WILL GIMME THE FUCKING SHITS"""
"""LIKE /status/job_id in which job_id will ecrypted text containing my bois request"""
"""ALSO /status/summary/url in which job_id will provide summary I think i should do it first"""


@api.get('/health')
def health():
    return {'health':200}


"""request:
    {}
    """



@api.post('/status/{video_id}')
async def query(video_id:str,request:QueryPayload,db:AsyncSession=Depends(get_db)):
    try:
        
        question=request.question

        

        full_summary=request.full_summary
        
        if len(full_summary)==4:
            full_summary=True

        else:
            full_summary=False

        uuid_term=str(uuid.uuid4())

        key=uuid_term

        create_table()

        print("TABLE CREATED OR NOT IDK")

        await create_job(db,job_id=key,video_id=video_id,question=question)

        print("JOB CREATED")

        print("KEY IS ",key)

        print("SLEEPING FOR 28 SECONDS")

        await asyncio.sleep(12)

        print("I AM aWAkE DUMBASS")
        
        msg_to_redis(r,key,value=Value(
            user_id=key,
            # message=[question]
            full_summary=full_summary,
            sender="Human"
        ))
        

        print("SENT TO THE REDIS BITCH")

        return {
            'response':'Ok so we are now gonna do someshit chef is ready and will cook :)',
            'job_id':key
        }

    except Exception as e:
        print("ERROR A AGYA HOGA BHADWE",e)


@api.websocket('/ws/status/{job_id}')
async def websocket_endpoint(websocket:WebSocket,job_id:str):
    """"Gonna dismantel the redis_listener into splitted personality and not a fucking funcition"""
    import os
    await websocket.accept()
    os.environ['REDIS_API_KEY'] = os.getenv('REDIS_API_KEY')

    # Connect to Redis
#     r = aioredis.from_url(
#     f"redis://default:{os.environ['REDIS_API_KEY']}@redis-12857.c62.us-east-1-4.ec2.redns.redis-cloud.com:12857/0",
#     decode_responses=True
# )

    from workers.celery_app import process_video_summary

    print("SERVER ONLINE")

    redis_url = f"redis://default:{os.getenv('REDIS_API_KEY')}@redis-12857.c62.us-east-1-4.ec2.redns.redis-cloud.com:12857/0"
    r = aioredis.from_url(redis_url, decode_responses=True)

    # await pubsub.subscribe('from_redis')
    pubsub = r.pubsub()
    await pubsub.subscribe('from_redis')

    

    print("SUBSCRIBED TO REDIS BY API  {job_id}NOW LISTENING")

    try:
        async for message in pubsub.listen():
            if message['type']=='message':
                channel=message['channel']
                print("CHANNEL NAME IS",channel)
                job_data = json.loads(message["data"])
                

                if job_data['user_id']!=job_id:
                    continue

                print("SENDING TO CELERY")
                
                
                print(f'New message on channel "from redis"')

                summary=""
                async with AsyncSessionLocal() as db:
                        job_info = await get_job(db, job_id=job_id)
                        if job_info:
                            summary = job_info['response'] # Assuming 'response' holds the summary
                    
                    # Send the final summary to the client
                print("GOT THE SUMMMARY BABYYYYYY",summary)
                await websocket.send_text(summary)
                break

    except Exception as e:
        print("ERROR OCCURED IN WEBSOCKET",e)

    finally:
        print(f"Client  disconnecting.")
        await pubsub.unsubscribe('from_redis')
        await r.close()
        await websocket.close()
                



                # x=r.blpop(job_data['user_id'],timeout=0)

                # print("USING HELL FROM ROUTES")

                # response=await send_to_hell.delay(job_data)
                # print("SENT HELL FROM ROUTES")


                # await websocket.send_text(response)

        

    



        


    #     from IPython.display import Image,display
    
    #     display(app.get_graph().draw_ascii())

    
    #     if full_summary:
    #         result=app2.invoke({
    #             'video_id':video_id,
    #             'documents':[],
    #             'question':'',
    #             'answer':""
    #         })
        
    #     else:
    #         result=app.invoke({
    #             'video_id':video_id,
    #             'documents':[],
    #             'question':question,
    #             'answer':"",
    #             # "full_summmary":full_summary
    #         })

    #     return {'response':result}

    # except Exception as e:
    #     print("ERROR A AGYA HOGA BHADWE",e)