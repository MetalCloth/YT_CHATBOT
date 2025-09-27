from langchain_anthropic import ChatAnthropic
import os
from ai_core.prompts import conditional_prompt,summarizing_prompt
from dotenv import load_dotenv
from langchain import tools
from langgraph.graph import START,END,StateGraph
from langchain_core.documents import Document
from database.vectorstore import Retriever,Store
from ai_core.utils import PreProcessing
from typing import TypedDict,Optional,List
from pydantic import BaseModel
load_dotenv()



os.environ['ANTHROPIC_API_KEY']=os.getenv('ANTHROPIC_API_KEY')

"""If the question is "Broad/Topic":
Perform a vector search only on your summarized DB. This will quickly find the summaries that are conceptually related to the user's question.
From the metadata of the matching summary documents, extract the list of original chunk IDs (raw_chunks_id).
Use those IDs to fetch the full, original documents directly from your raw DB.
These original, detailed documents become the context you send to the final LLM."""


"""If the question is "Specific/Factual":
Ignore the summary DB. You need the raw details.
Perform a Hybrid Search (Vector Search + Keyword Search) directly on your raw DB.
The keyword search is essential here. It will find the exact variable names, commands, or proper nouns that a pure vector search might miss.
These retrieved raw documents become the context.
"""

class Youtube(TypedDict):
    video_id:str
    question:str
    documents:List[Document]
    answer:str


# class Docs(BaseModel):
#     raw_docs:PreProcessing
#     summ_docs:PreProcessing
#     video_id:str


def ingesting_video(state:Youtube):
    """Does the basic ingesting """

    assert state['video_id']

    preprocess=PreProcessing(state['video_id'])
    preprocess.transcribing_video()
    raw_docs=preprocess.organising_transcript()
    summarized_docs=preprocess.summarizing_transcript(raw_docs)

    db_store = Store()
    db_store.ingesting_raw_docs(raw_docs)
    db_store.ingesting_summarized_docs(summarized_docs)



def condition(state:Youtube):
    assert state['question']

    model=ChatAnthropic(model='claude-sonnet-4-20250514')

    prompt=conditional_prompt()

    chain=prompt | model

    response=chain.invoke({'text':state['question']})

    if response.content.lower()=='specific_question':
        return 'raw'
    
    if response.content.lower()=='summary_request':
        return 'summary'
    

    
    

# @tools
def vector_search_for_summ_db(state:Youtube):
    """Uses vector search tool only for summarized DB From the metadata of the matching summary documents, 
    extract the list of original chunk IDs (raw_chunks_id).
    """

    summ_retriever=Retriever().summarized_retriever(k=3)

    response=summ_retriever.invoke(state['question'])
    state['documents'].append(response)
    return state


# @tools
def vector_search_for_raw_db(state:Youtube):
    """Uses vector search tool only for summarized DB From the metadata of the matching summary documents, 
    extract the list of original chunk IDs (raw_chunks_id).
    """

    raw_retriever=Retriever().raw_retriever(k=3)

    response=raw_retriever.invoke(state['question'])

    
    state['documents'].append(response)
    return state


def generate_response(state:Youtube):

    model=ChatAnthropic(model='claude-sonnet-4-20250514')
    prompt=summarizing_prompt()

    chain=prompt | model


    response=chain.invoke({'doc':state['documents']})

    state['answer']=response.content
    return state





graph=StateGraph(Youtube)

graph.add_node('ingestion',ingesting_video)
graph.add_node('raw_db',vector_search_for_raw_db)
graph.add_node('summ_db',vector_search_for_summ_db)
graph.add_node('generate_response',generate_response)

graph.add_edge(START,'ingestion')

graph.add_conditional_edges('ingestion',condition,
                            {
                                'raw':'raw_db',
                                'summary':'summ_db'
                            })

graph.add_edge('raw_db','generate_response')

graph.add_edge('summ_db','generate_response')

graph.add_edge('generate_response',END)

app=graph.compile()


if __name__=="__main__":

    from IPython.display import Image,display

    
    display(app.get_graph().draw_ascii())
    
    
    query=input('Enter your query')

    
    result=app.invoke({
        'video_id':'HdPzOWlLrbE',
        'documents':[],
        'question':query,
        'answer':""
    })


    print(result['answer'])