import youtube_transcript_api
from langchain_core.documents import Document
from youtube_transcript_api import YouTubeTranscriptApi
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_text_splitters import RecursiveCharacterTextSplitter
import uuid


model=ChatOllama(model='llama3')

prompt=ChatPromptTemplate.from_template(
    '''You are a summarizer agent who will summarize the given text AND ALSO JUST GIVE SUMMARY DONT TRY TO MAKE CONVERSATION LIKE 'HERE IS THE SUMMARY TYPE' THING AND ALSO MAKE SUMMARY SUCH THAT MAIN THINGS ARE NOT LOST 
    {doc}
    '''
)

chain=prompt | model

video_id='-8NURSdnTcg'

def preprocessing(video_id):
    transcript=YouTubeTranscriptApi()

    splitter=RecursiveCharacterTextSplitter(chunk_size=2000,chunk_overlap=400)
    script=transcript.fetch(video_id)

    transcript=" ".join([i.text for i in script.snippets])

    raw_docs=splitter.create_documents([transcript])

    for docs in raw_docs:
        docs.metadata['id']=str(uuid.uuid4())

    return raw_docs

def summarizing_each_doc(raw_docs,chunks_size=4):
    summarized_docs=[]
    for i in range(0, len(raw_docs), chunks_size):
        group = raw_docs[i:i+chunks_size]
        group_content = " ".join([doc.page_content for doc in group])

        metadata=[doc.metadata['id'] for doc in group]

        summary = chain.invoke({"doc": group_content})
        summarized_docs.append(Document(
            page_content=summary.content,
            metadata={
                "raw_chunks_id":metadata
            },
        ))

    return summarized_docs

