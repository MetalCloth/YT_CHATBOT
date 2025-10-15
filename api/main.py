import streamlit as st
import requests
import re

FASTAPI_URL = "http://127.0.0.1:8000"

# --- Helper Function ---
def extract_video_id(video_url_or_id):
    """
    Extracts the YouTube video ID from a URL or returns the ID if it's already an ID.
    """
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
        1.  **Start the Backend**: Make sure your FastAPI application (`main.py`) is running.
            ```bash
            uvicorn main:app --reload
            ```
        2.  **Enter Video Info**: Provide a YouTube video URL or just the 11-character Video ID.
        3.  **Ask a Question**: Type the question you have about the video content.
        4.  **Submit**: Click the "Get Answer" button and wait for the result below.
        """
    )

# --- Input Fields ---
st.header("Query Your Video")

video_input = st.text_input(
    "YouTube Video URL or ID",
    placeholder="e.g., Z9FBD9SwPmg or https://www.youtube.com/watch?v=Z9FBD9SwPmg"
)
question = st.text_area("What is your question?", placeholder="e.g., What is the main topic of the video?")
full_summary = st.checkbox("Generate a full summary of the video?")

# --- Submit Button and Logic ---
if st.button("Get Answer", type="primary"):
    if not video_input or (not question and not full_summary):
        st.warning("Please provide both a video ID/URL and a question.")
    
    else:
        video_id = extract_video_id(video_input)
        if not video_id:
            st.error("Invalid YouTube URL or Video ID. Please check your input.")
        else:
            with st.spinner(f"Processing video `{video_id}`... Please wait."):
                try:
                    # The endpoint URL for the POST request
                    endpoint = f"{FASTAPI_URL}/status/{video_id}"
                    
                    # The JSON payload for the request
                    # The backend expects a string, so we convert the boolean to a string.
                    if str(full_summary)==True:
                        ### CAUSE IT WONT MATTER HAHAHAAHHAHAHAHAH
                        question=''
                        
                    payload = {
                        "question": question,
                        "full_summary": str(full_summary)
                    }

                    # Make the POST request to the FastAPI backend
                    response = requests.post(endpoint, json=payload)

                    # st.write(response.content)
                    # Check the response status code
                    if response.status_code == 200:
                        st.success("Successfully received a response from the server!")
                        result = response.content.decode('utf-8')

                        # Display the result in a neat box
                        st.subheader("📝 Answer")
                        import json
                        st.write(json.loads(result))
                    else:
                        st.error(f"Failed to get a response from the server. Status code: {response.status_code}")
                        st.json(response.json())

                except requests.exceptions.RequestException as e:
                    st.error(f"Could not connect to the FastAPI backend at `{FASTAPI_URL}`.")
                    st.write("Please make sure the backend server is running and accessible.")
                    st.write(f"Error details: {e}")