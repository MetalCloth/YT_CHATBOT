from workers.task import app
from fastapi import FastAPI


x=FastAPI()

@x.get('/noob')
def function():
        result=app.invoke({
            'video_id':'-8NURSdnTcg',
            'documents':[],
            'question':'who is messmer',
            'answer':"",
            'full_summmary':True
        })
        print('-----ANSWER-----')

        print(result['answer'])

        return {'response':result['answer']}
        





# while True:
#         query=input('Enter your query')

#         result=app.invoke({
#             'video_id':'-8NURSdnTcg',
#             'documents':[],
#             'question':query,
#             'answer':""
#         })
#         print('-----ANSWER-----')

#         print(result['answer'])
