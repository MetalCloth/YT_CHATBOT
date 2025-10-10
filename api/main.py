import streamlit as st
import requests
import re
import time
import json

FASTAPI_URL = "http://127.0.0.1:8000"

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

st.set_page_config(page_title="Video Query App", layout="wide")

st.title("🎬 Asynchronous Video Query App")
st.markdown("This app uses a non-blocking FastAPI backend to process requests.")

with st.expander("How to use this app", expanded=True):
    st.info(
        """
        1.  **Start the Backend**: Make sure your FastAPI server (`fastapi_websocket_server.py`) is running.
            ```bash
            uvicorn fastapi_websocket_server:sio_app --reload
            ```
        2.  **Enter Video Info**: Provide a YouTube video URL or just the 11-character Video ID.
        3.  **Ask a Question**: Type your question or select the "full summary" option.
        4.  **Submit**: Click "Get Answer". The app will start the job and poll for the result automatically.
        """
    )

st.header("Query Your Video")

video_input = st.text_input(
    "YouTube Video URL or ID",
    placeholder="e.g., dQw4w9WgXcQ"
)
question = st.text_area("What is your question?", placeholder="e.g., What is the main topic of the video?")
full_summary = st.checkbox("Generate a full summary of the video?")

if 'job_id' not in st.session_state:
    st.session_state.job_id = None
if 'job_response' not in st.session_state:
    st.session_state.job_response = None
if 'job_failed' not in st.session_state:
    st.session_state.job_failed = False


if st.button("Get Answer", type="primary"):
    if not video_input or (not question and not full_summary):
        st.warning("Please provide a video ID/URL and either a question or select 'full summary'.")
    else:
        video_id = extract_video_id(video_input)
        if not video_id:
            st.error("Invalid YouTube URL or Video ID. Please check your input.")
        else:
            st.session_state.job_id = None
            st.session_state.job_response = None
            st.session_state.job_failed = False
            
            payload = {"question": question, "full_summary": full_summary}

            try:
                # STEP 1: START THE JOB by sending a POST request.
                start_endpoint = f"{FASTAPI_URL}/start-query/{video_id}"
                response = requests.post(start_endpoint, json=payload, timeout=10)
                response.raise_for_status()

                data = response.json()
                st.session_state.job_id = data.get("job_id")

                if not st.session_state.job_id:
                    st.error("Failed to start job: No job_id received from server.")
                else:
                    # STEP 2: POLL FOR THE RESULT using the new job_id.
                    with st.spinner(f"Job started (ID: {st.session_state.job_id}). Polling for result..."):
                        status_endpoint = f"{FASTAPI_URL}/status/{st.session_state.job_id}"
                        timeout = time.time() + 300 # 5-minute timeout
                        
                        while time.time() < timeout:
                            status_response = requests.get(status_endpoint, timeout=10)
                            status_response.raise_for_status()
                            status_data = status_response.json()
                            status = status_data.get('status')

                            if status == 'SUCCESS':
                                st.session_state.job_response = status_data.get('response')
                                st.session_state.job_failed = False
                                st.success("Job finished successfully!")
                                break
                            elif status == 'FAILED':
                                st.session_state.job_response = status_data.get('error', 'Unknown error.')
                                st.session_state.job_failed = True
                                st.error("Job failed.")
                                break
                            
                            # Wait for 5 seconds before checking again
                            time.sleep(5)
                        else:
                            st.error("Job timed out after 5 minutes.")

            except requests.exceptions.RequestException as e:
                st.error(f"Failed to communicate with the backend: {e}")

if st.session_state.job_id:
    st.write(f"**Last Job ID:** `{st.session_state.job_id}`")

if st.session_state.job_response:
    st.subheader("📝 Result")
    if st.session_state.job_failed:
        st.error(st.session_state.job_response)
    else:
        st.markdown(st.session_state.job_response)

