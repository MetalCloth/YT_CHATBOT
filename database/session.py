import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text 
import datetime
import uuid
from typing import List, Dict, Any

DATABASE_URL = "postgresql+asyncpg://postgres:19283746@localhost:5432/ytdb"

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def create_table():
    """
    Creates all tables if they don't exist.
    - data: Tracks the status of individual processing jobs.
    - chat_history: Stores the permanent messages for each session.
    """
    async with engine.begin() as conn:
        # --- JOB STATUS TABLE (Your existing table, UNCHANGED) ---
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

        # --- NEW: CHAT HISTORY TABLE ("The Notebook") ---
        await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id SERIAL PRIMARY KEY,
            session_id TEXT NOT NULL, 
            role TEXT NOT NULL, 
            content TEXT NOT NULL,
            timestamp TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() at time zone 'utc')
        );
        """))
        # Add an index for faster lookups by session
        await conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_chat_history_session_id
        ON chat_history (session_id, timestamp);
        """))

    print("TTHIS MESSAGE IS FROM SESSION.PY ables created or already exist.")

async def drop(conn:AsyncSession):
    # Modified to include the new table in the drop command
    await conn.execute(text(
        """DROP TABLE IF EXISTS chat_history, data;"""
    ))
    print("DTHIS MESSAGE IS FROM SESSION.PY ELETED ALL TABLES")


# --- JOB STATUS FUNCTIONS (Your existing functions, UNCHANGED) ---

async def create_job(conn:AsyncSession,job_id:str,video_id:str,question:str):
    await conn.execute(text("""
    INSERT INTO data (job_id,status,video_id,question) VALUES (:x,:y,:z,:a);
"""
    ),{"x":job_id,"y":"PENDING","z":video_id,"a":question})

    await conn.commit()

    print(f"THIS MESSAGE IS FROM SESSION.PY job created {job_id}")



async def get_job(conn:AsyncSession,job_id:str):

    response=await conn.execute(text("""
    SELECT * FROM data WHERE job_id=:job_id
""" 
    ),{'job_id':job_id})



    print('jTHIS MESSAGE IS FROM SESSION.PY ob is here')
    job = response.mappings().first()

    return job


async def update_job_status(conn:AsyncSession,job_id:str,status: str, summary: str):
    await conn.execute(text("""
    UPDATE data SET status=:status,response=:response WHERE job_id=:job_id
""" 
    ),{'status':status,'response':summary,'job_id':job_id})

    await conn.commit()

    print('cTHIS MESSAGE IS FROM SESSION.PY hanged job_status to SUCCESS')

async def delete_job(conn:AsyncSession,job_id:str):
    await conn.execute(text("""
    DELETE FROM data WHERE job_id=:job_id
""" 
    ),{'job_id':job_id})

    await conn.commit()

    print('DTHIS MESSAGE IS FROM SESSION.PY ELETED data')



async def add_chat_message(conn: AsyncSession, session_id: str, role: str, content: str):
    """Writes a new line in the session."""
    await conn.execute(text("""
    INSERT INTO chat_history (session_id, role, content)
    VALUES (:session_id, :role, :content)
    """), {"session_id": session_id, "role": role, "content": content})
    await conn.commit()
    print(f"THIS MESSAGE IS FROM SESSION.PY Saved chat message for session {session_id}")

async def get_chat_history(conn: AsyncSession, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Reads the last N lines from the session history."""
    result = await conn.execute(text("""
    SELECT role, content FROM (
        SELECT role, content, timestamp FROM chat_history
        WHERE session_id = :session_id
        ORDER BY timestamp DESC
        LIMIT :limit
    ) AS subquery
    ORDER BY timestamp ASC
    """), {"session_id": session_id, "limit": limit})
    
    messages = [{"role": row[0], "content": row[1]} for row in result.fetchall()]
    print(f"THIS MESSAGE IS FROM SESSION.PY Fetched {len(messages)} messages for session {session_id}")
    return messages