import fastapi
from requests import Request
from fastapi import FastAPI
from workers.task import app,app2
from pydantic import BaseModel
import json

api=FastAPI()


class QueryPayload(BaseModel):
    question: str
    full_summary: str = False

@api.get('/')
def root():
    return {'w':'welcome bhosadiwale'}



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
def query(video_id:str,request:QueryPayload):
    try:
        
        question=request.question

        full_summary=request.full_summary

        
        
        if len(full_summary)==4:
            full_summary=True

        else:
            full_summary=False

        from IPython.display import Image,display
    
        display(app.get_graph().draw_ascii())

    
        if full_summary:
            result=app2.invoke({
                'video_id':video_id,
                'documents':[],
                'question':'',
                'answer':""
            })
        
        else:
            result=app.invoke({
                'video_id':video_id,
                'documents':[],
                'question':question,
                'answer':"",
                # "full_summmary":full_summary
            })

        return {'response':result}

    except Exception as e:
        print("ERROR A AGYA HOGA BHADWE",e)

    



        


