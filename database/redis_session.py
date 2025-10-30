import redis
import dotenv
import time
from dotenv import load_dotenv
from pydantic import BaseModel
import uuid
from typing import TypedDict,Optional,List
import os

import json

"""First doing shit synchronously ok?"""

load_dotenv()

class Value(BaseModel):
    user_id:str 
    sender:str
    session_id: str 
    playlist_id:Optional[str]=None
    full_summary:Optional[bool]=False

os.environ['REDIS_API_KEY'] = os.getenv('REDIS_API_KEY')

r = redis.Redis(
    host='redis-12857.c62.us-east-1-4.ec2.redns.redis-cloud.com',
    port=12857,
    decode_responses=True,
    username="default",
    password=os.environ['REDIS_API_KEY']
)



x=r.keys("*")

def msg_to_redis(r:redis.Redis,key,value:Value,channel='to_redis'):
    """Sending message to redis"""

    print("STHIS MESSAGE IS FROM REDIS_SESSION.PY ENDING MESSAGE TO REDIS BY",value.sender)

    my_message={
        "user_id":key,
        'playlist_id':value.playlist_id,
        "sender":value.sender,
        "full_summary":value.full_summary,
        "session_id": value.session_id ,
    }

    json_msg=json.dumps(my_message)

    print("MTHIS MESSAGE IS FROM REDIS_SESSION.PY ESSAGE SEND TO REDIS",json_msg)

    r.rpush(key,json_msg)

    r.publish(channel,json_msg)



    print("STHIS MESSAGE IS FROM REDIS_SESSION.PY ENT MESSAGE TO",channel)
    


def receive_msg_from_redis(r:redis.Redis,key):
    """Recieveing message from the redis within a specific timeline bruv"""

    raw_msg=r.blpop(key,timeout=0)

    print("RTHIS MESSAGE IS FROM REDIS_SESSION.PY ECIEVING MESSAGE FROM REDIS BY BLPOP")

    if raw_msg:
        _, msg_bytes = raw_msg
        msg = json.loads(msg_bytes)
        print("MTHIS MESSAGE IS FROM REDIS_SESSION.PY ESSAGE IS", msg)
    else:
        print("NTHIS MESSAGE IS FROM REDIS_SESSION.PY O MESSAGE ARRIVED")

    return msg



def add_videos_to_session_redis(r: redis.Redis, session_id: str, video_ids: List[str]):
    """
    Adds one or more videos to the 'sessino.
    Uses SADD to automatically handle duplicates.
    """
    context_key = f"session_videos:{session_id}"
    r.sadd(context_key, *video_ids)
    r.expire(context_key, 86400) 
    print(f"THIS MESSAGE IS FROM REDIS_SESSION.PY Added videos {video_ids} to session {session_id}")

def get_session_videos_redis(r: redis.Redis, session_id: str) -> List[str]:
    """
    Gets all unique video IDs from the 'study room' (a Redis SET).
    """
    context_key = f"session_videos:{session_id}"
    video_ids = list(r.smembers(context_key))
    print(f"THIS MESSAGE IS FROM REDIS_SESSION.PY Retrieved {len(video_ids)} videos for session {session_id}")
    return video_ids



def redis_listener(r:redis.Redis):
    from workers.celery_app import process_video_summary

    pubsub = r.pubsub()
    pubsub.subscribe('to_redis')
    pubsub.subscribe('from_redis')

    print("TTHIS MESSAGE IS FROM REDIS_SESSION.PY  SUBSCRIBED TO REDIS PUBSUB")

    for message in pubsub.listen():

        if message['type'] == 'message':
            channel=message['channel']
            job_data = json.loads(message["data"])
            # The job_data now contains the 'session_id'
            
            print("STHIS MESSAGE IS FROM REDIS_SESSION.PY ENDING TO CELERY")

            print(f'THIS MESSAGE IS FROM REDIS_SESSION.PY New message on channel {channel}')

            if channel=='to_redis':
                print("STHIS MESSAGE IS FROM REDIS_SESSION.PY ENDING USER QUERY TO REDIS")
                process_video_summary.delay(job_data)
            
            


        
if __name__ == '__main__':
    redis_listener(r)