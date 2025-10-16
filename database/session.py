import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text 
import datetime


DATABASE_URL = "postgresql+asyncpg://postgres:19283746@localhost:5432/ytdb"

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def create_table():
    async with engine.begin() as conn:
        await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS data (
            id SERIAL PRIMARY KEY,
            job_id TEXT UNIQUE NOT NULL,
            video_id TEXT NOT NULL,
            question TEXT,
            status TEXT NOT NULL,
            response TEXT,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() at time zone 'utc')
        );
"""))
    print("table created")

async def drop(conn:AsyncSession):
    await conn.execute(text(
        """DROP TABLE IF EXISTS data;
"""
    ))
    print("DELETED")


async def create_job(conn:AsyncSession,job_id:str,video_id:str,question:str):
    await conn.execute(text("""
    INSERT INTO data (job_id,status,video_id,question) VALUES (:x,:y,:z,:a);
"""
        
    ),{"x":job_id,"y":"PENDING","z":video_id,"a":question})

    await conn.commit()

    print(f"job created {job_id}")



async def get_job(conn:AsyncSession,job_id:str):

    response=await conn.execute(text("""
    SELECT * FROM data WHERE job_id=:job_id
""" 
    ),{'job_id':job_id})



    print('job is here')
    job = response.mappings().first()

    return job


async def update_job_status(conn:AsyncSession,job_id:str,status: str, summary: str):
    await conn.execute(text("""
    UPDATE data SET status=:status,response=:response WHERE job_id=:job_id
""" 
    ),{'status':status,'response':summary,'job_id':job_id})

    await conn.commit()

    print('changed job_status to SUCCESS')

async def delete_job(conn:AsyncSession,job_id:str):
    await conn.execute(text("""
    DELETE FROM data WHERE job_id=:job_id
""" 
    ),{'job_id':job_id})

    await conn.commit()

    print('DELETED data')

# async def main():
#     await create_table()

#     async with AsyncSessionLocal() as db:
#         # await drop(db)
#         # print("DELETED THAT SHIT")
#         print("\n--- Running SQLAlchemy Core demo ---")
#         job_id = "test-job-7789"
#         video_id="ey2319"
#         question="What is this all about"
#         await create_job(db, job_id,video_id,question)
#         job=await get_job(db, job_id)

#         print(f"JOB IS {job} ")
# # JOB IS {'id': 1, 'job_id': 'test-job-7789', 'video_id': 'ey2319', 'question': 'What is this all about', 'status': 'PENDING', 'response': None, 'created_at': datetime.datetime(2025, 10, 16, 17, 24, 23, 257939)}
#         await update_job_status(db, job_id, "SUCCESS", "This is the final summary.")
#         await delete_job(db, job_id)

#         print("\n--- Demo finished ---")


# if __name__ == "__main__":
#     asyncio.run(main())

    



