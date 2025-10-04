from langchain_anthropic import ChatAnthropic
from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
import os
from ai_core.prompts import conditional_prompt,summarizing_prompt,chat_prompt
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
    summary_sections = preprocess.organising_summary_transcript()
    raw_docs = preprocess.recursive_chunk_snippets(chunk_size=500, chunk_overlap=100)
    print(f"Created {len(raw_docs)} raw document chunks.")
    summaries_mapped = preprocess.map_summaries_to_raw_by_time(summary_sections, raw_docs)
    

    db_store = Store(state['video_id'])
    db_store.ingesting_raw_docs(raw_docs)
    db_store.ingesting_summarized_docs(summaries_mapped)


def shortcut(state:Youtube):
    """Basically shortcut baby if to ingest or to continue"""

    db_store=Store(state['video_id'])

    
    verdict=db_store.collection_exists(state['video_id'])

    if verdict:
        return 'exist'
    
    else:
        return 'not_exist'


def condition(state:Youtube):
    assert state['question']

    # model=ChatAnthropic(model='claude-sonnet-4-20250514')
    # model=ChatOllama(model='llama3')
    model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
    
    # model=ChatGoogleGenerativeAI(model='llama3')

    prompt=conditional_prompt()

    chain=prompt | model

    response=chain.invoke({'text':state['question']})

    print(response.content)

    if response.content.lower()=='summary_request':
        return 'summary'
    
    elif response.content.lower()=='specific_question':
        return 'raw'
    
    elif response.content.lower()=='basic_conversation':
        return 'convo'
    
    
    # return 'summary'

# @tools
def vector_search_for_summ_db(state:Youtube):
    """Uses vector search tool only for summarized DB From the metadata of the matching summary documents, 
    extract the list of original chunk IDs (raw_chunks_id).
    """

    summ_retriever=Retriever(video_id=state['video_id']).summarized_retriever(k=3)

    response=summ_retriever.invoke(state['question'])

    state['documents'].append(response)
    return state


# @tools
def vector_search_for_raw_db(state:Youtube):
    """Uses vector search tool only for summarized DB From the metadata of the matching summary documents, 
    extract the list of original chunk IDs (raw_chunks_id).
    """

    """I will use summary retriever then i will use metaids from it to check the raw_retrirver 
    one and i will extract text from each metadata and boom"""


    # raw_retriever=Retriever().summarized_retriever(k=3)
    # pi=[]

    # for i in raw_retriever:
    #     x=i.metadata['raw_chunks_ids']
    #     pi=x.split(',')

    # if len(pi) > 5:
    #         pi = pi[:5]
    
    
    # for i in pi:
    print("HELLO WORLD")


    raw_retriever = Retriever(video_id=state['video_id']).summarized_retriever(k=3)
    all_raw_ids = []
    raw_retriever=raw_retriever.invoke(state['question'])



    for doc in raw_retriever:
        raw_ids = doc.metadata.get('raw_chunks_ids', [])
        # Always ensure it's a list
        if isinstance(raw_ids, str):
            raw_ids = raw_ids.split(',')
        # Limit number of chunks per summary doc
        if len(raw_ids) > 7:
            raw_ids = raw_ids[:7]
    

        all_raw_ids.extend(raw_ids)
    
    all_raw_ids = list(dict.fromkeys(all_raw_ids))[:10]

    store = Store(state['video_id'])
    raw_db = store.unsummarised_vectordb

    # Fetch all metadata
    all_docs = raw_db.get(include=['metadatas', 'documents'])  # 'documents' = page_content

    # Build a lookup dict by ID
    raw_lookup = {meta['id']: doc for meta, doc in zip(all_docs['metadatas'], all_docs['documents'])}

    # Get texts for the selected raw IDs
    texts = [raw_lookup[i] for i in all_raw_ids if i in raw_lookup]

        # texts = [all_docs[i] for i in all_raw_ids if i in all_docs]


    # response=raw_retriever.invoke(state['question'])

    """response gives a document brother"""

    
    state['documents'].append(texts)
    return state

def basic_conversation(state:Youtube):
    # model=ChatAnthropic(model='claude-sonnet-4-20250514')
    # model=ChatOllama(model='llama3')
    model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)


    prompt=chat_prompt()

    chain=prompt | model
    """Gonna give this shit convo history"""
    response=chain.invoke({'msg':state['question']})

    state['answer']=response.content

    return state

def generate_response(state:Youtube):
    # model=ChatAnthropic(model='claude-sonnet-4-20250514')
    # model=ChatOllama(model='llama3')
    model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

    prompt=summarizing_prompt()

    print('response prompt',prompt)

    chain=prompt | model

    response=chain.invoke({'ques':state['question'],'context':state['documents']})

    state['answer']=response.content

    return state

graph=StateGraph(Youtube)


graph.add_node('ingestion',ingesting_video)
graph.add_node('raw_db',vector_search_for_raw_db)
graph.add_node('summ_db',vector_search_for_summ_db)
graph.add_node('generate_response',generate_response)
graph.add_node('basic_conversation',basic_conversation)


graph.add_node('shortcut', lambda x: {})
graph.add_node('condition', lambda x: {})

# graph.add_node("shortcut", shortcut)
# graph.add_node("condition", condition)

graph.set_entry_point("shortcut")

# 3. Define the conditional logic using the routing functions
# Now this works because 'shortcut' is a known node.
graph.add_conditional_edges(
    'shortcut',
    shortcut,
    {
        'exist': 'condition',
        'not_exist': 'ingestion'
    }
)


graph.add_edge('ingestion','condition')

graph.add_conditional_edges(
    'condition',
    condition,
    {
        'summary':'summ_db',
        'raw':'raw_db',
        'convo':'basic_conversation'
    }
)

graph.add_edge('raw_db','generate_response')

graph.add_edge('summ_db','generate_response')

graph.add_edge('basic_conversation',END)

graph.add_edge('generate_response',END)

app=graph.compile()



if __name__=="__main__":

    from IPython.display import Image,display
    
    display(app.get_graph().draw_ascii())
    
    

    
    # ingesting_video(Youtube({'video_id':'-8NURSdnTcg','documents':[],'question':'','answer':''}))

    while True:
        query=input('Enter your query')

        result=app.invoke({
            'video_id':'-8NURSdnTcg',
            'documents':[],
            'question':query,
            'answer':""
        })
        print('-----ANSWER-----')

        print(result['answer'])
