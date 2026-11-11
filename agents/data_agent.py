import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.llm_config import llm_config
from utils.etl_tools import ETLTools
from models.schema import RouterSchema, DataAgentSchema
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain.tools import tool
from langgraph.graph import StateGraph, START, END
from agents.etl_analyst import etl_analyst
from agents.sql_analyst import sql_analyst


llm = llm_config()
llm_router = llm.with_structured_output(RouterSchema)


#-----------------------------------------------DATA AGENT GRAPH----------------------------------------------------

def router_node(state: DataAgentSchema):
    
    message = state.messages[-1].content
    
    router_prompt = (
    "Classify the user's request for routing only. "
    "Choose SQL for questions that query an existing database using SQL. "
    "Choose ETL for requests to extract, transform, or save data, "
    "including fetching data from a URL or creating a CSV. "
    "Return the required structured response; do not perform the requested task.\n\n"
    f"User request:\n{message}"
)

    route_response_dict = llm_router.invoke(router_prompt).model_dump()
    route_response = route_response_dict['answer']
    
    state.route_response = route_response
    
    return state
    
def etl_node(state: DataAgentSchema):
    
    message = state.messages[-1].content
    
    response = etl_analyst.invoke(
              {"messages":[HumanMessage(content= message)]})
    
    state.messages = state.messages + response["messages"]

    return state

def sql_node(state: DataAgentSchema):
    
    message = state.messages[-1].content
    
    input_schema = {
            "messages": [],
            "user_question": f"{message}",
            "curated_user_prompt": " ",
            "prompt_query_context": " ",
            "generated_sql_query": " ",
            "sql_query_execution_result": "",
            "is_safe" : "No",
            "comment": "",  
            "final_answer": " "
        }
        
        
    response = sql_analyst.invoke(input_schema)
    
    state.messages = state.messages + response["messages"]
    
    return state

data_agent_graph = StateGraph(DataAgentSchema)

#Nodes

data_agent_graph.add_node("router_node",router_node)
data_agent_graph.add_node("etl_node",etl_node)
data_agent_graph.add_node("sql_node", sql_node)

#Edges
data_agent_graph.add_edge(START,"router_node")

def is_sql_or_etl(state: DataAgentSchema):
    
    answer = state.route_response
    
    if answer == "SQL":
        return "sql_node"
    else:
        return "etl_node"
    
data_agent_graph.add_conditional_edges("router_node",is_sql_or_etl,{
    "sql_node":"sql_node",
    "etl_node": "etl_node"
})
data_agent_graph.add_edge("sql_node",END)
data_agent_graph.add_edge("etl_node",END)

data_agent = data_agent_graph.compile()

if __name__ == "__main__":
    
    response = data_agent.invoke({
        "messages": [HumanMessage(content="I want to extract the state, year and population only from the API endpoint 'https://api.datausa.io/tesseract/data.jsonrecords?cube=acs_yg_total_population_5&measures=Population&include=Year:2023&drilldowns=State,Year' and save it to data/extract folder in the csv folder ")],
        "route_response" : ""
    })
    
    print(response)