from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma

"""ITS BASIC PURPOSE IS TO FUCKING SPLIT AND RETURN RETRIEVER THATS ALL OK?"""


class Store:
    """Stores into 2 vectorstores one for summarized one for raw and they are interconnected using uuid"""

    def __init__(self):
        self.embeddings=OllamaEmbeddings(model='snowflake-arctic-embed:latest')
        self.unsummarised_vectordb=Chroma(collection_name="un_summarized_db",embedding_function=self.embeddings,persist_directory='./unsummarised_docs')
        self.summarised_vectordb=Chroma(collection_name="summarized_db",embedding_function=self.embeddings,persist_directory='./summarised_docs')

    def ingesting_raw_docs(self,raw_docs):
        """Ingesting raw_docs"""
        try:
            if raw_docs:
                self.unsummarised_vectordb.add_documents(raw_docs)
        
        except Exception as e:
            print(f'Error maybe the raw_docs is not made or vectordb is fuckedup Real error is btw {e}')

        print('Ingesting raw_docs successful')

    def ingesting_summarized_docs(self,summarized_docs):
        """Ingesting summarized_docs"""
        try:
            if summarized_docs:
                self.summarised_vectordb.add_documents(summarized_docs)
        
        except Exception as e:
            print(f'Error maybe the summarized_docs is not made or vectordb is fuckedup Real error is btw {e}')

        print('Ingesting summarized_docs successful')


class Retriever:
    """Makes a fucking retriever to do shits in this"""

    def __init__(self):
        self.vectorstore=Store()
        
    def raw_retriever(self,k=2):
        """End result returns retriever"""
        un_summarized_retriever=self.vectorstore.unsummarised_vectordb.as_retriever( search_type="similarity",search_kwargs={"k":k})

        return un_summarized_retriever
    

    def summarized_retriever(self,k=2):
        """End result returns retriever"""
        summarized_retriever=self.vectorstore.summarised_vectordb.as_retriever(search_type="similarity",search_kwargs={"k":k})

        return summarized_retriever

