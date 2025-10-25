# YT Chatbot: Asynchronous RAG Pipeline

**Query YouTube videos in real-time with an asynchronous RAG pipeline powered by FastAPI, Celery, LangGraph, and WebSockets.**

This project is a scalable, asynchronous system for chatting with YouTube videos. It ingests video transcripts, processes them through an intelligent RAG (Retrieval-Augmented Generation) pipeline, and delivers answers to users in real-time.

It's designed to handle long-running tasks without blocking the user, using Celery for background processing, PostgreSQL for job tracking, Redis for task queuing, and WebSockets for pushing results back to the client.

## 🌟 Core Features

* **Asynchronous Processing:** Uses **Celery** and **Redis** to offload heavy AI and ingestion tasks to background workers, ensuring the API remains fast and responsive.
* **Real-time Notifications:** Leverages **WebSockets** to push results back to the user the moment a job is complete, eliminating the need for polling.
* **Persistent Job Tracking:** Uses **PostgreSQL** to create and track the state of each user's request (e.g., `PENDING`, `SUCCESS`).
* **Automatic Transcript Ingestion:** Uses `youtube_transcript_api` to fetch video transcripts.
* **Intelligent Query Routing:** Uses a **LangGraph**-powered agent to classify user queries as "broad," "specific," or "conversational" to select the best retrieval strategy.
* **Hierarchical RAG Pipeline:**
    * **LLM-Powered Chaptering:** On first ingestion, an LLM (via `utils.py`) reads the *entire* transcript and divides it into logical, summarized chapters.
    * **Dual Vector Stores:** The system maintains two **ChromaDB** collections:
        1.  A `raw_docs` store with small, raw transcript chunks.
        2.  A `summarised_docs` store with the LLM-generated chapter summaries.
    * **Smart Retrieval:** Broad questions search the summary store, while specific questions search the summary store *first* to find the relevant chapter, then use its metadata to retrieve the corresponding *raw chunks* for a highly detailed and accurate answer.

## 🏗️ Architecture Flow

[Architecture Diagram]

1.  **WebSocket Connection & Job Creation:**
    * A user connects to the **FastAPI** server via a WebSocket (`/ws/status/{job_id}`).
    * To start a new job, the user hits the `POST /status/{video_id}` endpoint.
    * FastAPI creates a `PENDING` job in the **PostgreSQL** database and publishes the new `job_id` to a **Redis** (Pub/Sub) channel (`to_redis`).

2.  **Background Processing (Celery):**
    * A `redis_listener` (`redis_session.py`) is subscribed to the `to_redis` channel.
    * When a new job message is received, it triggers a **Celery** task (`celery_app.py`).

3.  **The LangGraph Pipeline (The "Brain"):**
    * The Celery worker executes the core **LangGraph** application (`task.py`).
    * **Shortcut Node:** The graph first checks if the video's vector embeddings already exist in **ChromaDB**.
    * **Ingestion Node (if new):**
        * Transcribes the video (`utils.py`).
        * Uses an LLM to generate logical chapters/summaries (`dividing_prompt`).
        * Creates raw chunks (`recursive_chunk_snippets`).
        * Populates both `raw_docs` and `summarised_docs` vector stores (`vector_store.py`).
    * **Condition Node:** The graph uses an LLM to classify the user's question (`conditional_prompt`).
    * **RAG Nodes:**
        * `summary_request`: Performs RAG on the `summarised_docs` store.
        * `specific_question`: Performs the hierarchical RAG (summary store -> raw store).
        * `full_summary`: Fetches all chapter summaries to assemble a full debrief.
    * **Generation Node:** The retrieved context is passed to a final LLM (`summarizing_prompt`) to generate the answer.

4.  **Job Completion & Notification:**
    * The Celery worker updates the job in **PostgreSQL** to `SUCCESS` and writes the final answer.
    * The worker then publishes a "job complete" message to the `from_redis` channel.
    * The **FastAPI** WebSocket listener (`main.py`) receives this message, fetches the result from PostgreSQL, and sends the final answer to the correct user over their WebSocket connection.

## 🛠️ Tech Stack

* **Backend:** FastAPI, Celery
* **Databases:**
    * **PostgreSQL (asyncpg):** Job/state management.
    * **Redis:** Task queue broker & Pub/Sub messaging.
    * **ChromaDB:** Persistent vector store for RAG.
* **AI & Orchestration:**
    * **LangGraph:** For building the core stateful, agentic workflow.
    * **LangChain:** For LLM chains, prompts, and document handling.
    * **LLMs:** Flexible design supporting `ChatGoogleGenerativeAI`, `ChatAnthropic`, `ChatOllama`, etc.
* **Data Ingestion:** `youtube_transcript_api`, `yt-dlp` (for playlists)
* **Tooling:** Pydantic, SQLAlchemy (async)

## 📁 Project Structure
```text
.
├── ai_core/
│   ├── prompts.py
│   ├── utils.py
│   ├── database/
│   │   ├── redis_session.py
│   │   └── session.py
│   ├── vector_store.py
│   └── workers/
├── celery_app.py
├── task.py
├── .env
├── main.py
└── requirements.txt
```

## 🚀 Getting Started

### 1. Prerequisites

* Python 3.10+
* PostgreSQL server
* Redis server
* Ollama (if using local embeddings/models)

### 2. Installation

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/your-username/your-repo-name.git](https://github.com/your-username/your-repo-name.git)
    cd your-repo-name
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set up environment variables:**
    Create a `.env` file and populate it with your credentials:
    ```.env
    # LLM APIs
    ANTHROPIC_API_KEY=...
    GOOGLE_API_KEY=...
    GROQ_API_KEY=...

    # Database URLs
    DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/ytdb
    REDIS_URL=redis://default:password@your-redis-host:port/0

    # For Redis connection in redis_session.py (if not using REDIS_URL)
    REDIS_HOST=...
    REDIS_PORT=...
    REDIS_API_KEY=...
    ```

### 3. Running the Application

You need to run three separate processes in different terminals.

1.  **Run the FastAPI Server:**
    ```bash
    uvicorn main:api --reload
    ```

2.  **Run the Celery Worker:**
    ```bash
    celery -A workers.celery_app.app worker --loglevel=info -P gevent
    ```

3.  **Run the Redis Listener:**
    This script subscribes to the Redis Pub/Sub channel to trigger Celery tasks.
    ```bash
    python -m database.redis_session
    ```

## 📡 API Endpoints

### Create a New Job

Submits a new video for processing.

`POST /status/{video_id}`

**Request Body:**

```json
{
  "question": "What is the main idea of this video?",
  "full_summary": false
}
```


WebSocket Connection
Connect to this endpoint to receive the final result once processing is complete.

WS /ws/status/{job_id}

Client: Connects to ws://localhost:8000/ws/status/a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8

Server: Once the job is SUCCESS, the server will push a JSON string containing the final answer.
