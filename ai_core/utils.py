from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import ChatOllama
import youtube_transcript_api
from langchain_groq import ChatGroq
from ai_core.prompts import dividing_prompt
import os
import json
from dotenv import load_dotenv
from typing import List
from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel,Field
load_dotenv()

os.environ['ANTHROPIC_API_KEY']=os.getenv('ANTHROPIC_API_KEY')
os.environ['GROQ_API_KEY']=os.getenv('GROQ_API_KEY')
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from youtube_transcript_api import YouTubeTranscriptApi
import uuid
from langchain_chroma import Chroma
from langchain.output_parsers import PydanticOutputParser

"""PREPROCESSING AND CONVERTING TO RAW AND SUMM DOCS"""

"""ADDING TIMESTAMP LATER ON"""


class Section(BaseModel):
    title: str = Field(..., description="Chapter title")
    summary: str
    start_time: str
    end_time: str

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

    def __init__(self,video_id):
        """Initializes Transcription for the video using video_id"""
        self.video_id=video_id
        self.transcript=""
    

    def transcribing_video(self):
        """Transcibes video like converting given yt video into text"""
        transcript=YouTubeTranscriptApi()
        script=""
        try:
            script=transcript.fetch(video_id=self.video_id)


        except Exception as e:
            print(f'Transcript failure for the video_id {self.video_id} Reason may be video_id is wrong The real error is {e}')

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
            doc.metadata['title']=i.title
            doc.metadata['start_time']=self.hhmmss_to_seconds(i.start_time)
            doc.metadata['end_time']=self.hhmmss_to_seconds(i.end_time)

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

    


    
if __name__=="__main__":
    # preprocess = PreProcessing(video_id='-8NURSdnTcg')
    # preprocess.transcribing_video()

    # # Chunk raw transcript
    # raw_docs = preprocess.recursive_chunk_snippets(chunk_size=500, chunk_overlap=100)

    # # Generate summaries with timestamps

    # summaries = preprocess.organising_summary_transcript()

    # # Map summaries to overlapping raw chunks
    # summaries_mapped = preprocess.map_summaries_to_raw_by_time(summaries, raw_docs)
    # # Check mapping
    # for summ in summaries_mapped[:2]:
    #     print(summ.metadata)

    preprocess = PreProcessing(video_id='IubDIhCxDTc')
    preprocess.transcribing_video()
    summary_sections = preprocess.organising_summary_transcript()
    raw_docs = preprocess.recursive_chunk_snippets(chunk_size=500, chunk_overlap=100)
    print(f"Created {len(raw_docs)} raw document chunks.")
    summaries_mapped = preprocess.map_summaries_to_raw_by_time(summary_sections, raw_docs)
    
    print(summaries_mapped)




