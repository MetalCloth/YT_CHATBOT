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
from typing import TypedDict,Optional,List,Dict,Any
from pydantic import BaseModel
load_dotenv()



os.environ['ANTHROPIC_API_KEY']=os.getenv('ANTHROPIC_API_KEY')

class Youtube(TypedDict):
    video_id:str               
    question:str
    documents:List[Document]
    answer:str
    playlist_id:Optional[str]
    session_id: str              
    chat_history: List[Dict[str, Any]] 


# class Docs(BaseModel):
#     raw_docs:PreProcessing
#     summ_docs:PreProcessing
#     video_id:str


def ingesting_video(state:Youtube):
    
    """Does the basic ingesting """
    
    video_id_to_ingest = state['video_id']
    
    assert video_id_to_ingest
    print(f"THIS MESSAGE IS FROM TASK.PY--- STARTING INGESTION for new video: {video_id_to_ingest} ---")
    
    preprocess=PreProcessing(video_id_to_ingest, playlist_id=state.get('playlist_id'))
    preprocess.transcribing_video()
    if not preprocess.transcript:
        print(f"THIS MESSAGE IS FROM TASK.PY FAILED: Could not get transcript for {video_id_to_ingest}")
        return state 

    summary_sections = preprocess.organising_summary_transcript()
    raw_docs = preprocess.recursive_chunk_snippets(chunk_size=500, chunk_overlap=100)
    print(f"THIS MESSAGE IS FROM TASK.PYCreated {len(raw_docs)} raw document chunks.")
    summaries_mapped = preprocess.map_summaries_to_raw_by_time(summary_sections, raw_docs)
    

    db_store = Store()
    
    db_store.ingesting_raw_docs(raw_docs)
    db_store.ingesting_summarized_docs(summaries_mapped)

    print(f'THIS MESSAGE IS FROM TASK.PY--- INGESTION COMPLETE for {video_id_to_ingest} ---')
    return state
    
def shortcut(state:Youtube):
    """
    Checks if ingestion is needed FOR ANY VIDEO in the session.
    This is now the "Ingestion Shortcut" manager.
    """
    print('--- THIS MESSAGE IS FROM TASK.PYIn Shortcut Node ---')
    video_id_input_string = state['video_id']
    db_store = Store()

    video_ids_to_process = [vid for vid in video_id_input_string.split(',') if vid]
    new_videos_found = False

    for video_id in video_ids_to_process:
        print(f"THIS MESSAGE IS FROM TASK.PYChecking ingestion status for: {video_id}")
        is_ingested = db_store.collection_exists(video_id)
        
        if not is_ingested:
            print(f"THIS MESSAGE IS FROM TASK.PYVideo {video_id} is NEW. Triggering ingestion.")
            new_videos_found = True
            ingest_state = state.copy()
            ingest_state['video_id'] = video_id
            ingesting_video(ingest_state)
            
        else:
            print(f"THIS MESSAGE IS FROM TASK.PYVideo {video_id} already in library. Skipping.")

    print("--- THIS MESSAGE IS FROM TASK.PYShortcut Node Complete. Proceeding to condition. ---")
    
    return state
    
def condition(state:Youtube):
    assert state['question']
    print('cTHIS MESSAGE IS FROM TASK.PYhecking if summary or specific question')

    if state['question'] == "GENERATE FULL SUMMARY":
        return 'summary_db_full' 

    model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

    prompt=conditional_prompt()
    chain=prompt | model
    response=chain.invoke({'text':state['question']})
    
    classification = response.content.lower()

    if 'summary_request' in classification:
        return 'summary'
    
    elif 'specific_question' in classification:
        return 'raw'
    
    elif 'basic_conversation' in classification:
        return 'convo'
    
    else:
        print(f"THIS MESSAGE IS FROM TASK.PYWarning: Unknown classification '{classification}'. Defaulting to 'raw'.")
        return 'raw'

def _build_search_filter(state: Youtube) -> dict:
    """Helper function to build the correct Chroma filter for ALL videos in the session."""
    video_id_str = state.get('video_id') 
    
    if not video_id_str:
        print("WTHIS MESSAGE IS FROM TASK.PYarning: No video_id string found in state.")
        return {}

    video_ids_list = video_id_str.split(',')
    video_ids_list = [vid for vid in video_ids_list if vid]
    if not video_ids_list:
        print("WTHIS MESSAGE IS FROM TASK.PYarning: No video_IDs found after splitting.")
        return {}

    search_filter = {
        "video_id": {
            "$in": video_ids_list
        }
    }
    print(f"THIS MESSAGE IS FROM TASK.PYFiltering search for {len(video_ids_list)} video(s).")
    return search_filter


def vector_search_for_summ_db(state:Youtube):
    """(Summary Request) Vector search on summarized DB, scoped to session videos."""
    print('sTHIS MESSAGE IS FROM TASK.PYearching for answer in summary_db')
    
    summ_retriever=Retriever().summarized_retriever(k=5)

    search_filter = _build_search_filter(state)
    if not search_filter:
        state['documents'] = []
        return state

    summ_retriever.search_kwargs = {"k": 5, "filter": search_filter}
    response = summ_retriever.invoke(state['question'])
    state['documents'] = response
    return state

def vector_search_for_raw_db(state:Youtube):
    """(Specific Question) Vector search on raw DB, scoped to session videos."""
    print('cTHIS MESSAGE IS FROM TASK.PYhecking for answer in raw db')

    raw_retriever = Retriever().summarized_retriever(k=5)
    
    search_filter = _build_search_filter(state)
    if not search_filter:
        state['documents'] = []
        return state

    raw_retriever.search_kwargs = {"k": 5, "filter": search_filter}
    summary_docs_found = raw_retriever.invoke(state['question'])

    all_raw_ids=[]
    for doc in summary_docs_found:
        raw_ids = doc.metadata.get('raw_chunks_ids', [])
        if isinstance(raw_ids, str):
            raw_ids = raw_ids.split(',')
        if len(raw_ids) > 7:
            raw_ids = raw_ids[:7]
        all_raw_ids.extend(raw_ids)
    
    all_raw_ids = list(dict.fromkeys(all_raw_ids))[:10]

    if not all_raw_ids:
        print("NTHIS MESSAGE IS FROM TASK.PYo raw IDs found from summaries.")
        state['documents'] = []
        return state
    
    print(f"THIS MESSAGE IS FROM TASK.PYFetching {len(all_raw_ids)} raw chunks by ID...")
    store = Store()
    raw_db = store.unsummarised_vectordb
    
    # Fetch all metadata
    all_docs = raw_db.get(ids=all_raw_ids,include=['metadatas', 'documents']) 

    texts = []
    for i in range(len(all_docs['ids'])):
        texts.append(
            Document(
                page_content=all_docs['documents'][i],
                metadata=all_docs['metadatas'][i]
            )
        )
    
    state['documents']=texts
    return state

def summarize_whole(state:Youtube):
    """
    (Full Summary Request) Gets ALL summary chunks for ALL videos in the session.
    """
    print("STHIS MESSAGE IS FROM TASK.PYTARTING FULL SUMMARY (summarize_whole node)")
    try:
        store = Store()
        db = store.summarised_vectordb

        # 1. Build the multi-video filter
        search_filter = _build_search_filter(state)
        if not search_filter:
            state['documents'] = []
            return state
        
        raw_result = db.get(
            where=search_filter,
            include=['metadatas', 'documents']
        )

        if not raw_result or not raw_result.get('ids'):
            print("WTHIS MESSAGE IS FROM TASK.PYarehouse is empty for this filter. No documents found.")
            state['documents'] = []
            return state
        
        all_details = []
        for i in range(len(raw_result['ids'])):
            metadata = raw_result['metadatas'][i]
            content = raw_result['documents'][i]
            details = {
                'video_id': metadata.get('video_id', 'N/A'), 
                'title': metadata.get('title', 'No Title Found'),
                'start_time': metadata.get('start_time', 'N/A'),
                'end_time': metadata.get('end_time', 'N/A'),
                'page_content': content
            }
            all_details.append(details)
        
        print(f"THIS MESSAGE IS FROM TASK.PYHeist successful. Retrieved details for {len(all_details)} documents.")
        state['documents'] = all_details 
        print("ETHIS MESSAGE IS FROM TASK.PYNDED FULL SUMMARY (summarize_whole node)")
        return state

    except Exception as e:
        print(f"THIS MESSAGE IS FROM TASK.PYHeist failed. An occurred: {e}")
        state['documents'] = []
        return state
    
def summary_generator(state:Youtube):
    """(Full Summary Request) Generates the final formatted summary report."""
    print("DTHIS MESSAGE IS FROM TASK.PYOING FULL SUMMARY_GENERATOR")
    model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

    prompt=fucking_summarizer()
    chain=prompt | model

    print("DTHIS MESSAGE IS FROM TASK.PYOCUMENTS (for full summary):", state['documents'])
    
    response=chain.invoke({
        'context':state['documents']
    })

    print(response.content)

    state['answer']=response.content
    print("DTHIS MESSAGE IS FROM TASK.PYONE FULL SUMARY_GENERATOR")
    return state
        
def basic_conversation(state:Youtube):
    """(Basic Chat) Handles simple conversation, with chat history."""
    print("RTHIS MESSAGE IS FROM TASK.PYunning basic_conversation node")
    model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)


    prompt=chat_prompt()
    chain=prompt | model

    history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in state['chat_history']])

    response=chain.invoke({
        'msg': state['question'],
        'context': history_str
        })

    state['answer']=response.content
    return state

def generate_response(state:Youtube):
    """(Q&A) Generates a RAG answer, aware of chat history."""
    print("RTHIS MESSAGE IS FROM TASK.PYunning generate_response node (RAG Q&A)")
    model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

    prompt=summarizing_prompt()
    chain=prompt | model

    history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in state['chat_history']])
    rag_context = "\n---\n".join([doc.page_content for doc in state['documents']])
    
    combined_context = f"""### PREVIOUS CHAT HISTORY:
{history_str}

### RELEVANT VIDEO CONTEXT (from {state['video_id']}):
{rag_context}
"""
    # -----------------------------------------------------------------

    response=chain.invoke({
        'ques': state['question'],
        'context': combined_context 
        })

    state['answer']=response.content
    return state

graph=StateGraph(Youtube)
graph2=StateGraph(Youtube)

graph2.add_node('summary_db_full', summarize_whole)
graph2.add_node('generate_summary', summary_generator)

graph2.set_entry_point("summary_db_full") 

graph2.add_edge('summary_db_full', 'generate_summary')
graph2.add_edge('generate_summary', END)
graph.add_node('raw_db', vector_search_for_raw_db)
graph.add_node('summ_db', vector_search_for_summ_db)
graph.add_node('generate_response', generate_response)
graph.add_node('basic_conversation', basic_conversation)
graph.add_node('shortcut', shortcut) 

graph.add_node('summary_db_full', graph2.compile()) 

graph.set_entry_point("shortcut")
graph.add_conditional_edges(
    'shortcut', 
    condition,  
    {
        'summary':'summ_db',
        'raw':'raw_db',
        'convo':'basic_conversation',
        'summary_db_full': 'summary_db_full'
    }
)

graph.add_edge('raw_db','generate_response')
graph.add_edge('summ_db','generate_response')
graph.add_edge('summary_db_full', END)
graph.add_edge('basic_conversation', END)
graph.add_edge('generate_response', END)

qa_app=graph.compile()
summary_app=graph2.compile() 

if __name__=="__main__":
    document=[]

    from IPython.display import Image,display
    
    import shutil
    
    display(summary_app.get_graph().draw_ascii())

    test_state = {
        'video_id': "7tOLcNZfPso,6h6dhevlb0w", 
        'documents': [],
        'question': 'What is a 10x engineer',
        'answer': "",
        'session_id': 'test_session_123',
        'chat_history': [
            {
                "role": "human",
                "content": "Can you give me a full summary of this video?"
            },
            {
                "role": "ai",
                "content": "**Video 1: Intro to Git (IubDIhCxDTc)**\n* (0:05 - 1:30) This chapter introduces Git..."
            },
            {
                "role": "human",
                "content": "What did it say about 'branching'?"
            },
            {
                "role": "ai",
                "content": "The video explains that branching is a core concept where you..."
            }
        ]
    }

    result = summary_app.invoke(test_state)
    print("_THIS MESSAGE IS FROM TASK.PY_______ANSWER______________")
    print(result['answer'])