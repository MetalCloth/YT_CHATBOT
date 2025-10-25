from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import ChatOllama
import youtube_transcript_api
from langchain_groq import ChatGroq
from ai_core.prompts import dividing_prompt
import os
import json
import yt_dlp
from dotenv import load_dotenv
from typing import List,Optional
from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel,Field
load_dotenv()
from langchain_google_genai import ChatGoogleGenerativeAI

os.environ['ANTHROPIC_API_KEY']=os.getenv('ANTHROPIC_API_KEY')
os.environ['GOOGLE_API_KEY']=os.getenv('GOOGLE_API_KEY')
os.environ['GROQ_API_KEY']=os.getenv('GROQ_API_KEY')
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from youtube_transcript_api import YouTubeTranscriptApi
import uuid
from langchain_chroma import Chroma
from langchain.output_parsers import PydanticOutputParser

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import WebshareProxyConfig

"""PREPROCESSING AND CONVERTING TO RAW AND SUMM DOCS"""

"""ADDING TIMESTAMP LATER ON"""


class Section(BaseModel):
    # playlist_id:str
    title: str = Field(..., description="Chapter title")
    summary: str
    start_time: str
    end_time: str
    # video_id:str

# FIX 1: Create a wrapper model to hold the list of sections
class Sections(BaseModel):
    sections: List[Section]

# FIX 2: Point the parser to the new wrapper model
parser = PydanticOutputParser(pydantic_object=Sections)


model=ChatOllama(model='llama3')

prompt=ChatPromptTemplate.from_template(
    '''You are a summarizer agent who will summarize the given text AND ALSO JUST GIVE SUMMARY DONT TRY TO MAKE CONVERSATION LIKE 'HERE IS THE SUMMARY TYPE' THING AND ALSO MAKE SUMMARY SUCH THAT MAIN THINGS ARE NOT LOST 
    {doc}
    '''
)

chain=prompt | model


class PreProcessing:
    """Uses basic principle of ingestion and preparing transcript"""

    def __init__(self,video_id:str=None,playlist_id:Optional[str]=None):
        """Initializes Transcription for the video using video_id"""
        self.video_id=video_id
        self.playlist_id=playlist_id
        self.transcript=""
    

    def transcribing_video(self):
        """Transcibes video like converting given yt video into text"""
        transcript = YouTubeTranscriptApi()
        script=""
        try:


            script=transcript.fetch(video_id=self.video_id)


        except Exception as e:
            print(f'Transcript failure for the video_id {video_id} Reason may be video_id is wrong The real error is {e}')

        self.transcript=script

        print('Transcription is done')
    
    def recursive_chunk_snippets(self, chunk_size=500, chunk_overlap=100):
        """
        snippets: list of transcript snippet objects with text, start, duration
        chunk_size: approx number of chars per chunk
        chunk_overlap: number of chars to overlap between chunks
        """
        docs = []
        temp_text = ""
        temp_start = None
        temp_end = None
        temp_snippets = []

        for snip in self.transcript:
            if temp_start is None:
                temp_start = snip.start
            
            temp_text += snip.text + " "
            temp_end = snip.start + snip.duration
            temp_snippets.append(snip)

            if len(temp_text) >= chunk_size:
                docs.append(Document(
                    page_content=temp_text.strip(),
                    metadata={
                        'video_id':self.video_id,
                        'playlist_id':self.playlist_id,
                        'id': str(uuid.uuid4()),
                        'start_time': temp_start,
                        'end_time': temp_end
                    }
                ))

                # Handle overlap
                if chunk_overlap > 0:
                    overlap_text = temp_text[-chunk_overlap:]
                    overlap_snips = []
                    acc_len = 0
                    for s in reversed(temp_snippets):
                        acc_len += len(s.text)
                        overlap_snips.insert(0, s)
                        if acc_len >= chunk_overlap:
                            break
                    temp_text = " ".join([s.text for s in overlap_snips])
                    temp_start = overlap_snips[0].start
                    temp_snippets = overlap_snips
                else:
                    temp_text = ""
                    temp_start = None
                    temp_snippets = []

        # Add any leftover
        if temp_text.strip():
            docs.append(Document(
                page_content=temp_text.strip(),
                metadata={
                    'video_id':self.video_id,
                    'playlist_id':self.playlist_id,
                    'id': str(uuid.uuid4()),
                    'start_time': temp_start,
                    'end_time': temp_end
                }
            ))

        return docs

    
    # def summarizing_transcript(self,raw_docs,chunks_size=4):
    #     """Taking multiple chunks of text and make a summary out of the combined minions"""
    #     summarized_docs=[]
    #     for i in range(0,len(raw_docs),chunks_size):
    #         group=raw_docs[i:i+chunks_size]
    #         group_content=" ".join([doc.page_content for doc in group])
    #         metadata_ids=[doc.metadata['id'] for doc in group]
    #         summary=chain.invoke({'doc':group_content})
    #         ids_as_string = ",".join(metadata_ids)
    #         summarized_docs.append(Document(
    #             page_content=summary.content,
    #             metadata={
    #                 'raw_chunks_id':ids_as_string
    #             }
    #         ))
        
    #     return summarized_docs

    @staticmethod
    def _seconds_to_hhmmss(seconds: float) -> str:
        """Helper function to convert seconds to HH:MM:SS format."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"
    
    @staticmethod
    def hhmmss_to_seconds(time_string: str) -> int:
        """
        Converts a time string in HH:MM:SS format to the total number of seconds.
        """
        # Split the string into hours, minutes, and seconds
        h, m, s = map(int, time_string.split(':'))
        
        # Calculate the total seconds using the formula: (h * 3600) + (m * 60) + s
        return (h * 3600) + (m * 60) + s
    
    def organising_summary_transcript(self):
        """Converting into splitted text using Recursive Text Splitter"""
        
        # FIX 1: Use a valid and powerful Groq model
        model = ChatGroq(model='meta-llama/llama-4-scout-17b-16e-instruct')
        
        prompt = dividing_prompt()
        # The parser is now correctly defined outside the class
        chain = prompt | model | parser
        formatted_transcript = ""
        for snippet in self.transcript:
            start_time_str = self._seconds_to_hhmmss(snippet.start)
            text = snippet.text
            formatted_transcript += f"[{start_time_str}] {text}\n"

        response = chain.invoke({'transcript': formatted_transcript})

        docs=[]
        for i in response.sections:
            doc=Document(
                page_content=i.summary
            )
            doc.metadata['playlist_id']=self.playlist_id
            doc.metadata['title']=i.title
            doc.metadata['start_time']=self.hhmmss_to_seconds(i.start_time)
            doc.metadata['end_time']=self.hhmmss_to_seconds(i.end_time)
            doc.metadata['video_id']=self.video_id
            

            docs.append(doc)

        return docs

            

    @staticmethod
    def map_summaries_to_raw_by_time(summaries: list[Document], raw_docs: list[Document]):
        """
        Link each summary doc to all raw docs that overlap in time
        """
        for summary in summaries:
            sum_start = summary.metadata['start_time']
            sum_end = summary.metadata['end_time']

            linked_raw_ids = []
            for raw in raw_docs:
                raw_start = raw.metadata['start_time']
                raw_end = raw.metadata['end_time']

                # Check if times overlap
                if not (raw_end < sum_start or raw_start > sum_end):
                    linked_raw_ids.append(raw.metadata['id'])

            summary.metadata['raw_chunks_ids'] = linked_raw_ids

        return summaries

    @staticmethod
    def get_playlist_video_ids(playlist_url):
        """Uses yt-dlp to extract all video IDs from a playlist."""
        ydl_opts = {
        'extract_flat': True,  # Don't download, just get the info
        'quiet': True,         # Suppress yt-dlp's console output
    }
    
        video_ids = []
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                # Extract playlist info
                playlist_info = ydl.extract_info(playlist_url, download=False)
                
                if 'entries' in playlist_info:
                    for video in playlist_info['entries']:
                        if video and 'id' in video:
                            video_ids.append(video['id'])
                print(f"Found {len(video_ids)} videos in the playlist.")
                
            except Exception as e:
                print(f"Error extracting playlist info: {e}")
                return None
                
        return video_ids
    

## vibecoded from here
if __name__=="__main__":
    
    # 1. DEFINE YOUR TEST IDs
    TEST_VIDEO_ID = 'IubDIhCxDTc' # A short video
    TEST_PLAYLIST_ID = None
    
    print(f"--- Testing PreProcessing with video_id: {TEST_VIDEO_ID} and playlist_id: {TEST_PLAYLIST_ID} ---")

    # 2. INITIALIZE THE CLASS with both IDs
    preprocess = PreProcessing(video_id=TEST_VIDEO_ID, playlist_id=TEST_PLAYLIST_ID)
    
    print("\n[1/3] Transcribing video...")
    preprocess.transcribing_video()
    if not preprocess.transcript:
        print("🔴 FAILED: Could not fetch transcript. Exiting.")
        exit()
    print("✅ Transcription complete.")

    # 3. TEST RAW CHUNKS
    print("\n[2/3] Generating raw document chunks...")
    raw_docs = preprocess.recursive_chunk_snippets()
    print(f"✅ Generated {len(raw_docs)} raw chunks.")
    
    if raw_docs:
        print("\n--- Checking metadata for raw_docs[0] ---")
        first_raw_meta = raw_docs[0].metadata
        print(first_raw_meta)
        
        # Check the tags
        if first_raw_meta.get('video_id') == TEST_VIDEO_ID:
            print("✅ video_id tag is correct.")
        else:
            print(f"❌ FAILED: video_id tag is missing or incorrect!")
            
        if first_raw_meta.get('playlist_id') == TEST_PLAYLIST_ID:
            print("✅ playlist_id tag is correct.")
        else:
            print(f"❌ FAILED: playlist_id tag is missing or incorrect!")
    else:
        print("⚠️ No raw docs generated.")
        
    # 4. TEST SUMMARY SECTIONS
    print("\n[3/3] Generating summary sections...")
    summary_sections = preprocess.organising_summary_transcript()
    print(f"✅ Generated {len(summary_sections)} summary sections.")

    if summary_sections:
        print("\n--- Checking metadata for summary_sections[0] ---")
        first_summ_meta = summary_sections[0].metadata
        print(first_summ_meta)
        
        # Check the tags
        if first_summ_meta.get('video_id') == TEST_VIDEO_ID:
            print("✅ video_id tag is correct.")
        else:
            print(f"❌ FAILED: video_id tag is missing or incorrect!")
            
        if first_summ_meta.get('playlist_id') == TEST_PLAYLIST_ID:
            print("✅ playlist_id tag is correct.")
        else:
            print(f"❌ FAILED: playlist_id tag is missing or incorrect!")
    else:
        print("⚠️ No summary sections generated.")
        
    print("\n--- Test Complete ---")