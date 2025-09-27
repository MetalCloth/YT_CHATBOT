from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import ChatOllama
import youtube_transcript_api
from prompts import dividing_prompt
import os
import json
from dotenv import load_dotenv
load_dotenv()
os.environ['ANTHROPIC_API_KEY']=os.getenv('ANTHROPIC_API_KEY')
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from youtube_transcript_api import YouTubeTranscriptApi
import uuid
from langchain_chroma import Chroma

"""PREPROCESSING AND CONVERTING TO RAW AND SUMM DOCS"""

"""ADDING TIMESTAMP LATER ON"""


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
        subtitles=""
        try:
            script=transcript.fetch(video_id=self.video_id)

            subtitles=" ".join([i.text for i in script.snippets])


        except Exception as e:
            print(f'Transcript failure for the video_id {self.video_id} Reason may be video_id is wrong The real error is {e}')

        self.transcript=subtitles
        print('Transcription is done')
    
    def organising_transcript(self):
        """Converting into splitted text using Recursive Text Splitter"""
        splitter=RecursiveCharacterTextSplitter(chunk_size=500,chunk_overlap=100)

        raw_docs=splitter.create_documents([self.transcript])

        for docs in raw_docs:
            docs.metadata['id']=str(uuid.uuid4())

        return raw_docs
    
    def summarizing_transcript(self,raw_docs,chunks_size=4):
        """Taking multiple chunks of text and make a summary out of the combined minions"""
        summarized_docs=[]
        for i in range(0,len(raw_docs),chunks_size):
            group=raw_docs[i:i+chunks_size]
            group_content=" ".join([doc.page_content for doc in group])
            metadata_ids=[doc.metadata['id'] for doc in group]
            summary=chain.invoke({'doc':group_content})
            ids_as_string = ",".join(metadata_ids)
            summarized_docs.append(Document(
                page_content=summary.content,
                metadata={
                    'raw_chunks_id':ids_as_string
                }
            ))
        
        return summarized_docs
    
    def organising_summary_transcript(self):
        """Converting into splitted text using Recursive Text Splitter"""
        model=ChatAnthropic(model='claude-sonnet-4-20250514',max_tokens_to_sample=4096)

        prompt=dividing_prompt()

        chain=prompt | model

        response=chain.invoke({'transcript':str(self.transcript)})

        s=json.loads(response.content)
        docs=[]

        for content in s:
            doc=Document(page_content=content['summary'])
            doc.metadata['id']=str(uuid.uuid4())
            doc.metadata['title']=content['title']
            doc.metadata['start_time']=content['start_time']
            doc.metadata['end_time']=content['end_time']

            docs.append(doc)

        
        summary_docs=docs

        return summary_docs

    


if __name__=="__main__":
    preprocess=PreProcessing(video_id='-8NURSdnTcg')
    preprocess.transcribing_video()

    
