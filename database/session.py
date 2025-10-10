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
        CREATE TABLE IF NOT EXISTS jobs (
            id SERIAL PRIMARY KEY,
            job_id TEXT UNIQUE NOT NULL,
            status TEXT NOT NULL,
            response TEXT,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() at time zone 'utc')
        );
"""))
    print("table created")


async def create_job(conn:AsyncSession,job_id:str):
    await conn.execute(text("""
    INSERT INTO jobs (job_id,status) VALUES (:x,:y);
"""
        
    ),{"x":job_id,"y":"PENDING"})

    await conn.commit()

    print(f"job created {job_id}")



async def get_job(conn:AsyncSession,job_id:str):

    response=await conn.execute(text("""
    SELECT * FROM jobs WHERE job_id=:job_id
""" 
    ),{'job_id':job_id})



    print('job is here')
    job = response.mappings().first()

    return job


async def update_job_status(conn:AsyncSession,job_id:str,status: str, summary: str):
    await conn.execute(text("""
    UPDATE jobs SET status=:status,response=:response WHERE job_id=:job_id
""" 
    ),{'status':status,'response':summary,'job_id':job_id})

    await conn.commit()

    print('changed job_status to SUCCESS')

async def delete_job(conn:AsyncSession,job_id:str):
    await conn.execute(text("""
    DELETE FROM jobs WHERE job_id=:job_id
""" 
    ),{'job_id':job_id})

    await conn.commit()

    print('DELETED jobs')

async def main():
    await create_table()

    async with AsyncSessionLocal() as db:
        print("\n--- Running SQLAlchemy Core demo ---")
        job_id = "test-job-567"

        await create_job(db, job_id)
        await get_job(db, job_id)
        await update_job_status(db, job_id, "SUCCESS", "This is the final summary.")
        await delete_job(db, job_id)

        print("\n--- Demo finished ---")


if __name__ == "__main__":
    asyncio.run(main())

    

