""""ERROR MIGHT BE DUE TO UNABILITY TO UPDATE OR DELETE POSTGRESQL"""

import fastapi
from requests import Request

from fastapi import FastAPI,Depends,WebSocket
from workers.task import app,app2
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


@api.websocket('/ws')
async def websocket_endpoint(websocket:WebSocket):
    await websocket.accept()

    print("SERVER ONLINE")
    try:
        

    



        


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