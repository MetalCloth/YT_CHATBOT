from langchain_core.prompts import ChatPromptTemplate


def summarizing_prompt():
    return ChatPromptTemplate.from_template(
    '''You are a summarizer agent who will summarize the given text AND ALSO JUST GIVE SUMMARY DONT TRY TO MAKE CONVERSATION LIKE 'HERE IS THE SUMMARY OF THE TEXT BULLSHIT' THING AND ALSO MAKE SUMMARY SUCH THAT MAIN THINGS ARE NOT LOST 
    {doc}
    '''
)


def conditional_prompt():
    return ChatPromptTemplate.from_template(
    '''You are an expert at classifying user questions. Your job is to determine if the user is asking a "specific_question" or a "summary_request".
- "specific_question" is for when the user is asking about a precise detail, fact, name, or command.
- "summary_request" is for when the user is asking for a broader explanation of a topic or concept mentioned in the video.
Only respond with the category name and nothing else. HERE IS THE TEXT BELOW
    {text}
    '''
)   

def dividing_prompt():
    return ChatPromptTemplate.from_template("""You are an expert technical writer and content strategist. Your task is to analyze the following video transcript and segment it into logical, self-contained chapters based on the topics being discussed.

For each chapter you identify, you must provide:
1.  A short, descriptive **title** that captures the main topic.
2.  A detailed one-paragraph **summary** of the key information and concepts covered in that chapter.
3.  The precise **start and end timestamps** for that chapter.

Your final output must be a clean JSON array of objects, with no introductory text or conversational filler.

**Example JSON format:**

[
  {{
    "title": "Introduction to Kubernetes",
    "summary": "The speaker introduces the core concepts of Kubernetes...",
    "start_time": "00:00:00",
    "end_time": "00:05:12"
  }},
  {{
    "title": "Core Components: Pods, Nodes, and Services",
    "summary": "This section provides a deep dive into the fundamental building blocks...",
    "start_time": "00:05:13",
    "end_time": "00:12:45"
  }}
]
        HERE IS THE TRANSCRIPT
        {transcript}
    """ )
