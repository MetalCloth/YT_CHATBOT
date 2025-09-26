from langchain_core.prompts import ChatPromptTemplate


def summarizing_prompt():
    return ChatPromptTemplate.from_template(
    '''You are a summarizer agent who will summarize the given text AND ALSO JUST GIVE SUMMARY DONT TRY TO MAKE CONVERSATION LIKE 'HERE IS THE SUMMARY TYPE' THING AND ALSO MAKE SUMMARY SUCH THAT MAIN THINGS ARE NOT LOST 
    {doc}
    '''
)