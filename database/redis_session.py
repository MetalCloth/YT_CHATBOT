import redis
import dotenv
import time
from dotenv import load_dotenv
from pydantic import BaseModel
import uuid
from typing import TypedDict,Optional
import os
from workers.celery_app import process_video_summary

import json

"""First doing shit synchronously ok?"""

load_dotenv()

class Value(BaseModel):
    user_id:str
    # message:list[str]
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

# r.flushall()
def msg_to_redis(r:redis.Redis,key,value:Value):
    """Sending message to redis
    {msg_to_redis(r,key,value=Value(
            user_id=key,
            # message=[question,video_id],
            full_summary=full_summary,
            sender="API"
        ))}
    """

    my_message={
        "user_id":key,
        # "message":value.message,
        "sender":"Human",
        "full_summary":value.full_summary
    }

    json_msg=json.dumps(my_message)

    print("JSON",json_msg)

    r.rpush(key,json_msg)

    r.publish('redis_changes',json_msg)



    print("SENT MESSAGE STRAIGHT TO REDIS")

    


def receive_msg_from_redis(r:redis.Redis,key):
    """Recieveing message from the redis within a specific timeline bruv"""

    raw_msg=r.blpop(key,timeout=0)

    if raw_msg:
        _, msg_bytes = raw_msg
        msg = json.loads(msg_bytes)
        print("MESSAGE IS", msg)
    else:
        print("NO MESSAGE ARRIVED")

    return msg


def redis_listener(r:redis.Redis):
    pubsub = r.pubsub()
    pubsub.subscribe('redis_changes')

    print("SUBSCRIBED TO REDIS PUBSUB")

    for message in pubsub.listen():

        if message['type'] == 'message':
            job_data = json.loads(message["data"])
            print("SENDING TO CELERY")
            process_video_summary.delay(job_data)

        
if __name__ == '__main__':
    redis_listener(r)




# if __name__=="__main__":
     
#     key=str(uuid.uuid4())


     
    
#     msg_to_redis(r,key,value=Value(
#         message=["""Imagine Redis as a cosmic micro-metropolis, floating in the ether, with exactly 30 MB of inhabitable space. At first glance, 30 MB seems laughably tiny—like a shoebox in the middle of Times Square—but that’s deceptive. Each message you send is a tiny capsule apartment—304 bytes—compact, perfectly self-contained, like a Japanese pod hotel room. At first, you start tossing these capsules in, one after the other, thinking “how many could this possibly hold?” And then, boom—you realize that this shoebox can actually host over 103,450 of these apartments. One hundred thousand tiny lives, each neatly tracked, each accounted for. The city is alive. Each resident has a door, a mailbox, a nameplate—the works.

# But Redis isn’t just a barren building with capsules. No, no. Redis is a living, breathing city, complete with hallways, elevators, stairwells, security guards, and a meticulous administrative staff that keeps track of every single apartment. This is the metadata overhead. Every key you create, every value you store, eats up a tiny slice of space for bookkeeping—so while the theoretical max is 103,450 capsules, the real, fully functional, bustling city might host 80,000–90,000 residents. Still, that’s staggering density. Compare it to a normal apartment building: you’d need several square kilometers in the real world to host that many humans. Redis does it in 30 MB.

# Now, imagine if your capsules started getting fancier—each message grows from 304 bytes to 1 KB. Suddenly, that same high-rise micro-city can now only fit about 30,000 apartments. The elevators groan, the hallways feel tighter, and the once-efficient pod design starts feeling cramped. Every extra byte is like adding a couch, a fridge, and a chandelier to each pod—it sounds nice, but it eats into your limited space fast. And this is just message size—we haven’t even touched complex data structures yet. Redis lets you create hashes, lists, sets, and sorted sets—like building skyscrapers, warehouses, villas, and palaces instead of tiny pods. A single hash can hold thousands of mini-apartments under one roof—a super-efficient building design. Suddenly, your city isn’t just full; it’s architecturally genius, optimized for density, speed, and chaos.

# Now layer in activity. Your micro-metropolis isn’t static—messages arrive, expire, keys are deleted, TTLs tick down. Redis has to maintain all of this at lightning speed, keeping doors open, elevators running, hallways unclogged. It’s like running a real-time city simulation where every nanosecond counts. Each time a new message enters, Redis makes split-second decisions: which capsules to fit, which keys to evict if memory maxes out, how to reorganize structures to maintain optimal throughput. That’s why memory management and message sizing matter—one careless byte can ripple through the city like a traffic jam during rush hour.

# Let’s push it further. Imagine you start mixing message sizes: 304 bytes, 512 bytes, 1 KB, 2 KB—your city is now a mix of pod hotels, lofts, and mini-mansions. Redis has to juggle them all, balancing overhead, metadata, and actual payloads. Efficiency drops if you’re careless, but with smart planning—like using hashes or carefully managing TTLs—you can maintain a city of incredible density, with tens of thousands of messages flowing seamlessly. You can even implement memory eviction policies—like choosing which apartments to demolish when space runs out. LRU, LFU, all these are city management policies in action.

# And don’t forget persistence. You might want snapshots (RDB) or append-only logs (AOF). Now your 30 MB city also has archives—libraries, records, and vaults of every past resident. These take additional space but are essential if you want to survive disasters. Redis is tiny but resilient, compact but remarkably capable. It’s like a city designed by Tetris gods—every byte has its perfect place.

# So yes, 30 MB looks laughable on your monitor, but in Redis terms, it’s a miracle of dense, optimized living space. You can cram tens of thousands of messages, juggle overhead, and even scale up with clever structures and policies. Think of yourself as the mayor of this byte-sized metropolis: every decision—message size, key design, TTL, data structure—affects thousands of tiny lives. Mess up, and your city grinds to a halt. Plan well, and you’ll run one of the most efficiently packed data cities in existence, all in something smaller than a single picture on your screen.

# And if you’re visual, you can literally map it out: 30 MB as a grid, each 304-byte message a tiny square, overhead scattered around like parks and roads. Watch your population grow, shrink, and reorganize. That’s Redis, blud. Tiny, powerful, and shockingly dense.""","rsHq4NPDEs0"],
#         full_summary=False,
#         user_id=key,
#         sender="API"
#     ))

