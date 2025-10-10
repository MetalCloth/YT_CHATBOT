import streamlit as st
import requests
import re
import time
import json # Import json to parse the backend response

# --- Configuration ---
FASTAPI_URL = "http://127.0.0.1:8000"

# --- Helper Function ---
def extract_video_id(video_url_or_id):
    youtube_regex = (
        r'(https?://)?(www\.)?'
        '(youtube|youtu|youtube-nocookie)\.(com|be)/'
        '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')
    
    match = re.match(youtube_regex, video_url_or_id)
    
    if match:
        return match.group(6)
    
    if len(video_url_or_id) == 11 and not video_url_or_id.startswith("http"):
        return video_url_or_id

    return None

# --- Streamlit UI ---
st.set_page_config(page_title="Video Query App", layout="wide")

st.title("🎬 Video Query App")
st.markdown("This app lets you ask questions about a YouTube video. It uses a FastAPI backend to process the request.")

# --- Instructions ---
with st.expander("How to use this app", expanded=True):
    st.info(
        """
        1.  **Start the Backend**: Make sure your FastAPI + Socket.IO server (`fastapi_websocket_server.py`) is running.
            ```bash
            uvicorn fastapi_websocket_server:sio_app --reload
            ```
        2.  **Enter Video Info**: Provide a YouTube video URL or just the 11-character Video ID.
        3.  **Ask a Question**: Type the question you have about the video content.
        4.  **Submit**: Click "Start Query" to begin processing.
        5.  **Check Status**: Click "Check Job Status" periodically to see if your result is ready! (Streamlit cannot receive real-time pushes directly).
        """
    )

# --- Input Fields ---
st.header("Query Your Video")

video_input = st.text_input(
    "YouTube Video URL or ID",
    placeholder="e.g., Z9FBD9SwPmg or https://www.youtube.com/watch?v=Z9FBD9SwPmg",
    key="video_input" # Added a key for consistent state
)
question = st.text_area("What is your question?", placeholder="e.g., What is the main topic of the video?", key="question_input")
full_summary = st.checkbox("Generate a full summary of the video?", key="full_summary_checkbox")

# --- Session State for Job ID ---
if 'job_id' not in st.session_state:
    st.session_state.job_id = None
if 'job_status' not in st.session_state:
    st.session_state.job_status = "Not started"
if 'job_response' not in st.session_state:
    st.session_state.job_response = None

# --- Submit Button Logic ---
col1, col2 = st.columns([1, 1])

with col1:
    if st.button("Start Query", type="primary"):
        if not video_input or (not question and not full_summary):
            st.warning("Please provide both a video ID/URL and a question, or select full summary.")
        else:
            video_id = extract_video_id(video_input)
            if not video_id:
                st.error("Invalid YouTube URL or Video ID. Please check your input.")
            else:
                st.session_state.job_id = None # Reset job ID for new queries
                st.session_state.job_status = "Submitting..."
                st.session_state.job_response = None

                payload = {
                    "question": question,
                    "full_summary": full_summary # Send boolean, FastAPI will parse it
                }

                try:
                    # Make the POST request to the FastAPI backend to START the job
                    endpoint = f"{FASTAPI_URL}/start-query/{video_id}"
                    response = requests.post(endpoint, json=payload)
                    response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

                    data = response.json()
                    st.session_state.job_id = data.get("job_id")
                    st.session_state.job_status = "Job Started! ID: " + st.session_state.job_id + ". Click 'Check Status' below."
                    st.success(st.session_state.job_status)

                except requests.exceptions.RequestException as e:
                    st.session_state.job_status = "Error starting job."
                    st.error(f"Could not connect to the FastAPI backend at `{FASTAPI_URL}`.")
                    st.write("Please make sure the backend server is running and accessible.")
                    st.write(f"Error details: {e}")
                st.rerun() # Rerun to update state display immediately

with col2:
    if st.button("Check Job Status", type="secondary"):
        if st.session_state.job_id:
            with st.spinner(f"Checking status for Job ID `{st.session_state.job_id}`..."):
                try:
                    status_endpoint = f"{FASTAPI_URL}/status/{st.session_state.job_id}"
                    response = requests.get(status_endpoint)
                    response.raise_for_status()
                    
                    status_data = response.json()
                    st.session_state.job_status = f"Status: {status_data.get('status', 'Unknown')}"
                    
                    if status_data.get('status') == 'SUCCESS':
                        st.session_state.job_response = status_data.get('response')
                        st.success(f"Job {st.session_state.job_id} finished!")
                    elif status_data.get('status') == 'FAILED':
                        st.session_state.job_response = status_data.get('error', 'An unknown error occurred.')
                        st.error(f"Job {st.session_state.job_id} failed!")
                    else:
                        st.info(f"Job {st.session_state.job_id} is still {status_data.get('status', 'processing')}...")
                    
                except requests.exceptions.RequestException as e:
                    st.error(f"Error checking job status: {e}")
                st.rerun() # Rerun to update state display immediately
        else:
            st.info("No job has been started yet. Click 'Start Query' first.")

# --- Display Current Status & Results ---
st.subheader("Current Job Status")
st.write(f"**Job ID:** {st.session_state.job_id if st.session_state.job_id else 'N/A'}")
st.write(f"**Status:** {st.session_state.job_status}")

if st.session_state.job_response:
    st.subheader("📝 Answer")
    if isinstance(st.session_state.job_response, dict):
        st.json(st.session_state.job_response)
    else:
        st.write(st.session_state.job_response)

# ```

# ---

# ### **How to Run This Perfect Setup:**

# 1.  **Install Requirements:**
#     ```bash
#     pip install "python-socketio[asgi]" uvicorn fastapi pydantic streamlit requests
#     ```

# 2.  **Start Your Backend Server (Terminal 1):**
#     ```bash
#     uvicorn fastapi_websocket_server:sio_app --reload
#     ```
#     (Make sure this file is in your project root, or adjust the path.)

# 3.  **Start Your Streamlit Frontend (Terminal 2):**
#     ```bash
#     streamlit run streamlit_frontend.py
    
