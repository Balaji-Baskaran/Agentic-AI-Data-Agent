from agents.data_agent import data_agent
from langchain_core.messages import HumanMessage

def run():
    user_query = input("Tell the Task to Implement: ")
    response = data_agent.invoke({
        "messages": [HumanMessage(content=f"{user_query}")],
        "route_response": ""
    })
    
    last_message = response["messages"][-1]
    print(last_message.content if hasattr(last_message, "content") else last_message["content"])

if __name__ == "__main__":
    run()
