from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from transcribe import preprocessing,summarizing_each_doc

"""ITS BASIC PURPOSE IS TO FUCKING SPLIT AND RETURN RETRIEVER THATS ALL OK?"""


embeddings=OllamaEmbeddings(model='snowflake-arctic-embed:latest')
unsummarised_vectordb=Chroma(collection_name="transcriptvectordb",embedding_function=embeddings,persist_directory='./unsummarised_docs')
summarized_vectordb=Chroma(collection_name="transcriptvectordb",embedding_function=embeddings,persist_directory='./summarised_docs')

splitter=RecursiveCharacterTextSplitter(chunk_size=1000,chunk_overlap=200)


def raw_chunk_vectordb(video_id):
    raw_docs=preprocessing(video_id)

    summarized_docs=summarizing_each_doc(raw_docs,chunks_size=4)

    unsummarised_vectordb.aadd_documents(raw_docs)
    summarized_vectordb.aadd_documents(summarized_docs)

    print('Summarization is complete')






