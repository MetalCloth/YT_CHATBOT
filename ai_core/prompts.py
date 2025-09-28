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
- "specific_question" is for when the user is asking about a precise detail like u would need very very indepth answer for it.
- "summary_request" is for when the user is asking for a broader explanation of a topic or concept mentioned in the video.
Only respond with the category name and nothing else. HERE IS THE TEXT BELOW
    {text}
    '''
)   

def dividing_prompt():
    return ChatPromptTemplate.from_template("""
You are an expert technical writer and an exceptional summarizer, tasked with creating a structured, easy-to-read table of contents for a video transcript. Your goal is to analyze the transcript and segment it into logical, self-contained chapters.

For each chapter you identify, you must provide:
1.  A concise, descriptive **title** that captures the chapter's main topic.
2.  A high-quality, one-paragraph **summary** that adheres to the principles listed below.
3.  The precise **start and end timestamps** for that chapter.

---
### Summary Generation Principles
When writing the summary for each chapter, you absolutely must:
- **Capture the Core Essence:** Distill the most critical information, key arguments, and main conclusions presented in the chapter.
- **Be Comprehensive but Concise:** Mention all main topics discussed but avoid verbatim quotes, filler words, or overly granular details. The goal is to be thorough without being lengthy.
- **Identify Key Entities:** Include any important names, technologies, concepts, or organizations mentioned.
- **Maintain a Neutral Tone:** Summarize the content objectively, without injecting your own opinions or interpretations.
- **Ensure Readability:** Write a single, well-structured, and coherent paragraph that flows logically and is easy for a human to read and understand.
---

Your final output must be a single, clean JSON object.

**CRITICAL:** Do not add any introductory text, conversational filler, or markdown code blocks. Your response must begin IMMEDIATELY with the opening brace `{{` of the JSON object.

**Example JSON format:**
{{
  "sections": [
    {{
      "title": "Introduction to Kubernetes",
      "summary": "This chapter introduces the fundamental concepts of Kubernetes, explaining its purpose as a container orchestration platform. It covers the history of containerization, the problems Kubernetes solves (like scaling and deployment), and defines core terminology such as containers, pods, and nodes, setting the stage for a more detailed exploration of its architecture.",
      "start_time": "00:00:00",
      "end_time": "00:05:12"
    }},
    {{
      "title": "Core Components: Pods, Nodes, and Services",
      "summary": "A detailed breakdown of the primary components in the Kubernetes ecosystem. The summary explains the roles of Pods as the smallest deployable units, Nodes as the worker machines running the Pods, and Services as the abstraction layer for enabling network access to a set of Pods. It clarifies how these components interact to run an application.",
      "start_time": "00:05:13",
      "end_time": "00:12:45"
    }}
  ]
}}

HERE IS THE FULL VIDEO TRANSCRIPT TO ANALYZE:
{transcript}
""")