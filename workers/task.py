from langchain_anthropic import ChatAnthropic
from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
import os
from ai_core.prompts import conditional_prompt,summarizing_prompt,chat_prompt,fucking_summarizer
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
    playlist_id:Optional[str]

    # full_summmary:bool


# class Docs(BaseModel):
#     raw_docs:PreProcessing
#     summ_docs:PreProcessing
#     video_id:str


def ingesting_video(state:Youtube):
    
    """Does the basic ingesting """

    assert state['video_id']
    print("doing basic ingestion")
    preprocess=PreProcessing(state['video_id'],playlist_id=state.get('playlist_id'))
    preprocess.transcribing_video()
    summary_sections = preprocess.organising_summary_transcript()
    raw_docs = preprocess.recursive_chunk_snippets(chunk_size=500, chunk_overlap=100)
    print(f"Created {len(raw_docs)} raw document chunks.")
    summaries_mapped = preprocess.map_summaries_to_raw_by_time(summary_sections, raw_docs)
    

    db_store = Store()
    
    db_store.ingesting_raw_docs(raw_docs)
    db_store.ingesting_summarized_docs(summaries_mapped)

    print('ingestion compleete')
    


def shortcut(state:Youtube):
    """Basically shortcut baby if to ingest or to continue"""
    
    print('checking if ingestion needed')

    db_store=Store()

    
    verdict=db_store.collection_exists(state['video_id'])

    if verdict:
        return 'exist'
    
    else:
        return 'not_exist'


def condition(state:Youtube):
    assert state['question']
    print('checking if summary or specific question')

    # model=ChatAnthropic(model='claude-sonnet-4-20250514')
    # model=ChatOllama(model='llama3')
    model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
    
    # model=ChatGoogleGenerativeAI(model='llama3')

    prompt=conditional_prompt()

    chain=prompt | model

    response=chain.invoke({'text':state['question']})


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
    print('searching for answer in summary_db')
    

    summ_retriever=Retriever().summarized_retriever(k=5)
    search_filter = {}

    playlist_id = state.get('playlist_id')
    video_id = state.get('video_id')

    # 3. Build the filter logic
    if playlist_id and video_id:
        print(f"Filtering for playlist {playlist_id} AND video {video_id}")
        search_filter = {
            "$and": [
                {"playlist_id": playlist_id},
                {"video_id": video_id}
            ]
        }
    else:
        print(f"Filtering for single video {video_id}")
        search_filter = {"video_id": video_id}

    summ_retriever.search_kwargs = {"k": 3, "filter": search_filter}

    response=summ_retriever.invoke(state['question'])

    # state['documents'].append(response)
    state['documents']=response
    return state


# @tools
def vector_search_for_raw_db(state:Youtube):
    """Uses vector search tool only for summarized DB From the metadata of the matching summary documents, 
    extract the list of original chunk IDs (raw_chunks_id).
    """

    """I will use summary retriever then i will use metaids from it to check the raw_retrirver 
    one and i will extract text from each metadata and boom"""

    print('checking for asnwr in raw db')

    # raw_retriever=Retriever().summarized_retriever(k=3)
    # pi=[]

    # for i in raw_retriever:
    #     x=i.metadata['raw_chunks_ids']
    #     pi=x.split(',')

    # if len(pi) > 5:
    #         pi = pi[:5]
    
    
    # for i in pi:
    print("HELLO WORLD")


    raw_retriever = Retriever().summarized_retriever(k=5)
    search_filter={}

    playlist_id=state.get('playlist_id')
    video_id=state.get('video_id')

    if playlist_id and video_id:
        print(f"Filtering for playlist {playlist_id} AND video {video_id}")
        search_filter = {
            "$and": [
                {"playlist_id": playlist_id},
                {"video_id": video_id}
            ]
        }

    # elif playlist_id:
    #     # User gave only playlist: "Search the whole playlist"
    #     print(f"Filtering for entire playlist {playlist_id}")
    #     search_filter = {"playlist_id": playlist_id}
    else:
        # Fallback for /video/{video_id} endpoint (no playlist_id)
        print(f"Filtering for single video {video_id}")
        search_filter = {"video_id": video_id}    

    all_raw_ids = []
    raw_retriever.search_kwargs = {"k": 5, "filter": search_filter}


    raw_retriever=raw_retriever.invoke(state['question'])


    all_raw_ids=[]
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

    if not all_raw_ids:
        print("No raw IDs found from summaries.")
        state['documents'] = []
        return state
    
    print(f"Fetching {len(all_raw_ids)} raw chunks by ID...")
    store = Store()
    raw_db = store.unsummarised_vectordb

    # Fetch all metadata
    all_docs = raw_db.get(ids=all_raw_ids,include=['metadatas', 'documents'])  # 'documents' = page_content

    # Build a lookup dict by ID
    texts = []
    for i in range(len(all_docs['ids'])):
        texts.append(
            Document(
                page_content=all_docs['documents'][i],
                metadata=all_docs['metadatas'][i]
            )
        )

        # texts = [all_docs[i] for i in all_raw_ids if i in all_docs]


    # response=raw_retriever.invoke(state['question'])

    """response gives a document brother"""

    
    state['documents']=texts
    return state

def summarize_whole(state:Youtube):
    """
    This is the 'summary_db' node for graph2.
    It now correctly filters before getting all docs.
    """
    print("STARTING FULL SUMMARY")
    try:
        store = Store()
        db = store.summarised_vectordb

        # 1. Build the filter logic
        search_filter = {}
        playlist_id = state.get('playlist_id')
        video_id = state.get('video_id') # This is the OPTIONAL filter ID

        if playlist_id and video_id:
             print(f"Filtering summary for playlist {playlist_id} AND video {video_id}")
             search_filter = {"$and": [{"playlist_id": playlist_id}, {"video_id": video_id}]}
        # elif playlist_id:
        #      print(f"Filtering summary for entire playlist {playlist_id}")
        #      search_filter = {"playlist_id": playlist_id}
        else:
             print(f"Filtering summary for single video {state['video_id']}")
             search_filter = {"video_id": state['video_id']}
        
        # 2. Use .get() WITH A 'where' CLAUSE
        raw_result = db.get(
            where=search_filter,
            include=['metadatas', 'documents']
        )

        if not raw_result or not raw_result.get('ids'):
            print("Warehouse is empty for this filter. No documents found.")
            state['documents'] = []
            return state # Return state, not []
        
        all_details = []
        for i in range(len(raw_result['ids'])):
            metadata = raw_result['metadatas'][i]
            content = raw_result['documents'][i]
            details = {
                'title': metadata.get('title', 'No Title Found'),
                'start_time': metadata.get('start_time', 'N/A'),
                'end_time': metadata.get('end_time', 'N/A'),
                'page_content': content
            }
            all_details.append(details)
        
        print(f"Heist successful. Retrieved details for {len(all_details)} documents.")
        state['documents'] = all_details # Use =
        print("ENDED FULL SUMMARY")
        return state

    except Exception as e:
        print(f"Heist failed. An occurred: {e}")
        state['documents'] = []
        return state # Return state, not []
    
def summary_generator(state:Youtube):
    print("DOING FULL SUMMARY_GENERATOR")
    model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)


    # print("DOING FULL SUMMARY BABYYY")
    prompt=fucking_summarizer()

    chain=prompt | model

    print("DOCUMENTS",state['documents'])
    print("CHAIN",chain)
    

    response=chain.invoke({
        'context':state['documents']
    })

    print(response.content)

    
    print("DONE SHIT BROOO")

    state['answer']=response.content

    print("DONE FULL SUMARY_GENERATOR")

    return state
    # except Exception as e:
    #     print("MAHABALSESHWAR")
        


def basic_conversation(state:Youtube):
    # model=ChatAnthropic(model='claude-sonnet-4-20250514')
    # model=ChatOllama(model='llama3')
    model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)


    prompt=chat_prompt()

    chain=prompt | model
    """Gonna give this shit convo history"""
    response=chain.invoke({'msg':state['question'],'context':state['documents']})

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

graph2=StateGraph(Youtube)

graph2.add_node('ingestion',ingesting_video)

graph2.add_node('summary_db',summarize_whole)

graph2.add_node('generate_summary',summary_generator)


graph.add_node('ingestion',ingesting_video)
graph.add_node('raw_db',vector_search_for_raw_db)
graph.add_node('summ_db',vector_search_for_summ_db)
graph.add_node('generate_response',generate_response)
graph.add_node('basic_conversation',basic_conversation)


graph.add_node('shortcut', lambda x: {})
graph.add_node('condition', lambda x: {})

graph2.add_node('shortcut', lambda x: {})
graph2.set_entry_point("shortcut")

graph2.add_conditional_edges(
    'shortcut',
    shortcut,
    {
        'exist': 'summary_db',
        'not_exist': 'ingestion'
    }
)




graph.set_entry_point("shortcut")


# graph2.add_edge(START,'ingestion')
graph2.add_edge('ingestion','summary_db')
graph2.add_edge('summary_db','generate_summary')
graph2.add_edge('generate_summary',END)



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

app2=graph2.compile()

if __name__=="__main__":
    document=[]

    from IPython.display import Image,display
    
    import shutil
    # print("Cleaning up old databases...")
    # if os.path.exists('./unsummarised_docs'): shutil.rmtree('./unsummarised_docs')
    # if os.path.exists('./summarised_docs'): shutil.rmtree('./summarised_docs')
    # print("Cleanup complete.")
    display(app.get_graph().draw_ascii())

    # while True:
    #     query=input('Enter your query')

    #     result=app.invoke({
    #         'video_id':'Q5L0fycpQZI',
    #         'documents':document,
    #         'question':query,
    #         'answer':"",
    #         # "full_summmary":True
    #     })
    #     print('-----ANSWER-----')

    #     print(result['answer'])
    result =app2.invoke({
                    'video_id':"lyG52SEo4OM",
                    'documents': [],
                    'question': '',
                    'answer': ""
                })
    print("________ANSWER______________")

    print(result['answer'])