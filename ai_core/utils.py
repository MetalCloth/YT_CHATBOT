from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import ChatOllama
import youtube_transcript_api
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from youtube_transcript_api import YouTubeTranscriptApi
import uuid
from langchain_chroma import Chroma



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
        splitter=RecursiveCharacterTextSplitter(chunk_size=1000,chunk_overlap=200)

        raw_docs=splitter.create_documents([self.transcript])

        for docs in raw_docs:
            docs.metadata['id']=str(uuid.uuid4())

        return raw_docs
    
    def summarizing_transcript(raw_docs,chunks_size=4):
        """Taking multiple chunks of text and make a summary out of the combined minions"""
        summarized_docs=[]
        for i in range(0,len(raw_docs),chunks_size):
            group=raw_docs[i:i+chunks_size]
            group_content=" ".join([doc.page_content for doc in group])
            metadata=[doc.metadata['id'] for doc in group]
            summary=chain.invoke({'doc':group_content})
            summarized_docs.append(Document(
                page_content=summary.content,
                metadata={
                    'raw_chunks_id':metadata
                }
            ))
        
        return summarized_docs
    


if __name__=="__main__":
    preprocess=PreProcessing(video_id='-8NURSdnTcg')
    preprocess.transcribing_video()

    




