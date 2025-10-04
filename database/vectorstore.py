from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
import chromadb
from langchain_chroma import Chroma

"""ITS BASIC PURPOSE IS TO FUCKING SPLIT AND RETURN RETRIEVER THATS ALL OK?"""


class Store:
    """Stores into 2 vectorstores one for summarized one for raw and they are interconnected using uuid"""

    def __init__(self,video_id):
        self.embeddings=OllamaEmbeddings(model='snowflake-arctic-embed:latest')
        self.client1 = chromadb.PersistentClient(path='./unsummarised_docs')
        self.client2 = chromadb.PersistentClient(path='./summarised_docs')
        
        
        self.unsummarised_vectordb=Chroma(client=self.client1,collection_name=f"vid_{video_id}",embedding_function=self.embeddings)
        self.summarised_vectordb=Chroma(client=self.client2,collection_name=f"vid_{video_id}",embedding_function=self.embeddings)

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
                for doc in summarized_docs:
                    id_data=doc.metadata['raw_chunks_ids']
                    if isinstance(id_data, list):
                        print("Found a list, converting to string...")
                        doc.metadata['raw_chunks_ids'] = ",".join(id_data)


                self.summarised_vectordb.add_documents(summarized_docs)
        
        except Exception as e:
            print(f'Error maybe the summarized_docs is not made or vectordb is fuckedup Real error is btw {e}')

        print('Ingesting summarized_docs successful')

    
    def collection_exists(self,collection_name:str):
        """Checks if the collection name exists on the vectordb"""
        try:
            collection=self.client1.get_collection(name=f"vid_{collection_name}")
            item_count = collection.count()
            
            print(f"Collection '{collection_name}' found with {item_count} items.")
            if item_count<=0:
                return False
            
            print('client',self.client1)
            print(f"Collection '{collection_name}' found.")
            return True

        except ValueError:
            print(f"Collection '{collection_name}' not found.")
            return False


            

class Retriever:
    """Makes a fucking retriever to do shits in this"""

    def __init__(self,video_id):
        self.vectorstore=Store(video_id)
        
    def raw_retriever(self,k=2):
        """End result returns retriever"""
        un_summarized_retriever=self.vectorstore.unsummarised_vectordb.as_retriever( search_type="similarity",search_kwargs={"k":k})

        return un_summarized_retriever
    

    def summarized_retriever(self,k=2):
        """End result returns retriever"""
        summarized_retriever=self.vectorstore.summarised_vectordb.as_retriever(search_type="similarity",search_kwargs={"k":k})

        return summarized_retriever

