import redis
import dotenv
import time
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import TypedDict,Optional
import os
import json

"""First doing shit synchronously ok?"""

load_dotenv()

class Value(BaseModel):
    user_id:str
    message:list[str]
    sender:str
    full_summary:Optional[bool]=False

# Load Redis API key from .env
os.environ['REDIS_API_KEY'] = os.getenv('REDIS_API_KEY')

# Connect to Redis
r = redis.Redis(
    host='redis-12857.c62.us-east-1-4.ec2.redns.redis-cloud.com',
    port=12857,
    decode_responses=True,
    username="default",
    password=os.environ['REDIS_API_KEY']
)

x=r.keys("*")
print(r.keys("*"))

def msg_to_redis(r,key,value:Value):
    """Sending the message to the redis in form of key value pair where key is job_id and value is 
    {"user_id":"",
    "message":"",
    "sender":"",
    "full_summary":""
    }
    """
    r.rpush(key,json.dumps({"user_id":value.user_id,"message":value.message,"sender":value.sender,"full_summary":value.full_summary}))

    print("SEND THE MESSAGE")



def receive_msg_from_redis(r:redis.Redis,key):
    """Recieveing message from the redis within a specific timeline bruv"""

    raw_msg=r.blpop(key,timeout=0)

    if raw_msg:
        _, msg_bytes = raw_msg
        msg = json.loads(msg_bytes)
        print("MESSAGE IS", msg)
    else:
        print("NO MESSAGE ARRIVED")


