from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
import chromadb
from langchain_chroma import Chroma

"""ITS BASIC PURPOSE IS TO FUCKING SPLIT AND RETURN RETRIEVER THATS ALL OK?"""


class Store:
    """Stores into 2 vectorstores one for summarized one for raw and they are interconnected using uuid"""

    def __init__(self):
        self.embeddings=OllamaEmbeddings(model='snowflake-arctic-embed:latest')
        self.client1 = chromadb.PersistentClient(path='./unsummarised_docs')
        self.client2 = chromadb.PersistentClient(path='./summarised_docs')
        
        
        self.unsummarised_vectordb=Chroma(client=self.client1,collection_name="raw_db",embedding_function=self.embeddings)
        self.summarised_vectordb=Chroma(client=self.client2,collection_name="summ_db",embedding_function=self.embeddings)

    def ingesting_raw_docs(self,raw_docs):
        """Ingesting raw_docs"""
        try:
            if raw_docs:
                self.unsummarised_vectordb.add_documents(raw_docs)
        
        except Exception as e:
            print(f'THIS MESSAGE IS FROM VECTORSTORE.PY Error maybe the raw_docs is not made or vectordb is fuckedup Real error is btw {e}')

        print('ITHIS MESSAGE IS FROM VECTORSTORE.PY ngesting raw_docs successful')

    def ingesting_summarized_docs(self,summarized_docs):
        """Ingesting summarized_docs"""
        try:
            if summarized_docs:
                for doc in summarized_docs:
                    id_data=doc.metadata['raw_chunks_ids']
                    
                    if isinstance(id_data, list):
                        print("FTHIS MESSAGE IS FROM VECTORSTORE.PY ound a list, converting to string...")
                        doc.metadata['raw_chunks_ids'] = ",".join(id_data)


                self.summarised_vectordb.add_documents(summarized_docs)

            
        
        except Exception as e:
            print(f'THIS MESSAGE IS FROM VECTORSTORE.PY Error maybe the summarized_docs is not made or vectordb is fuckedup Real error is btw {e}')

        print('ITHIS MESSAGE IS FROM VECTORSTORE.PY ngesting summarized_docs successful')

    
    def collection_exists(self,video_id:str)->bool:
        """Checks if the collection name exists on the vectordb"""
        try:
            # Check the raw docs store. If it's here, the summary one should be too.
            collection = self.client1.get_collection(name="raw_db")
            result = collection.get(
                where={"video_id": video_id},
                limit=1
            )
            is_ingested = len(result['ids']) > 0
            print(f"THIS MESSAGE IS FROM VECTORSTORE.PY Check: Video {video_id} is ingested? {is_ingested}")
            return is_ingested
        except Exception as e:
            print(f"THIS MESSAGE IS FROM VECTORSTORE.PY Error checking if video is ingested: {e}")
            return False


            

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