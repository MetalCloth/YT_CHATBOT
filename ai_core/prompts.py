from langchain_core.prompts import ChatPromptTemplate


def summarizing_prompt():
    return ChatPromptTemplate.from_template(
    '''YOU ARE AN ANSWERING BOT WHO WILL ANSWER THE QUESTION BASED ON THE PROVIDED CONTEXT. ONLY GIVE ANSWER IN DETAIL RELATED TO THE ASKED QUESTION AND NOTHING MORE
    QUESTION:
    {ques}

    CONTEXT:
    {context}
    '''
)


def conditional_prompt():
    return ChatPromptTemplate.from_template(
    """
You are an expert classifier for video questions.  
Your job: read the user question and decide **exactly one label**: `summary_request` or `specific_question`.  
This will determine which database to use:

- `summary_request` → use the **summary DB** (broad, conceptual overview, main points).  
- `specific_question` → use the **raw DB** (detailed, step-by-step, exact facts, timestamps, code, numbers, examples).

RULES:

1) Classify as `specific_question` if the user asks for:
   - Exact steps, commands, code, formulas, calculations.
   - Specific examples, timestamps, quotes, logs, or debugging info.
   - Anything that cannot be answered from a summary alone.

2) Classify as `summary_request` if the user asks for:
   - High-level explanations, main points, or general understanding.
   - Overviews, themes, intuition, or broad concepts.
   - Anything that can be answered without exact details.

TIE-BREAKER:
- If the question contains both broad and specific aspects, choose `specific_question`.

**Output exactly one token**: `summary_request` or `specific_question`. No explanation, no quotes, no punctuation.

USER QUESTION:
{text}
"""
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