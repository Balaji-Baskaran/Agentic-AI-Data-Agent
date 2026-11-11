import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.llm_config import llm_config
from utils.etl_tools import ETLTools
from models.schema import ETLAgentSchema
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain.tools import tool
from langgraph.graph import StateGraph, START, END




#------------------------------------------------------------AGENT TOOLS ----------------------------------------------------------

@tool
def extract_load_tool(url: str, output_folder: str, format:str) -> str:
    """
    This tool extracts the data from the API (url) and loads it into the
    the desired location (output_folder).

    Args:
        url (str): The API endpoint from which to extract data.
        output_folder (str): The folder where the extracted data will be saved.
        format (str): The format in which to save the extracted data (csv, json, parquet).
    
    Returns:
        str: A message indicating the success or failure of the operation."""
        
    obj = ETLTools()
    return obj.extract_load(url, output_folder, format)


@tool
def transform_load_tool(input_file_path: str, output_folder: str, output_format: str, user_question) -> str:
    
    """
    This tool transforms the data from the specified file and loads it into the
    desired location (output_folder).

    Args:
        input_file_path (str): The path to the file containing the data to be transformed.
        output_folder (str): The folder where the transformed data will be saved.
        output_format (str): The format in which to save the transformed data (csv, json, parquet).
    
    Returns:
        str: A message indicating the success or failure of the operation.

    """
    
    obj = ETLTools()
    top_3_rows = obj.transform_load_context(input_file_path)
    
    llm = llm_config()
    
    prompt = f"""
            You are a Python Data Analyst who uses Pandas to analyze data. 
            You need to provide only the Pandas Code that will help to perform the right ETL operations on the data stored in the file : {input_file_path}
            as per the user's question. Do not provide any explanation or comments, only
            the code should be provided. The code should be in a format that can be executed 
            in a Python environment with Pandas installed. 
            Don't write anything else than Pandas Code. \n
            
            Create the Pandas Dataframe from the data stored in the file : {input_file_path} and then 
            write the code to transform and save the data at {output_folder}.
            Here's the user's question: {user_question}\n
            Here's the context of the data you will be analyzing: {top_3_rows}\n

        """
    
    response = llm.invoke(prompt).content
    
    pandas_code = response.strip().strip('```').strip().lstrip('python').strip()
    
    result = obj.execute_code(pandas_code)
    
    return f"The data is transformed and saved at {output_folder} in {output_format} format.\n Pandas Code: {pandas_code} and the result is {result}"

#Toolkit
tools = [extract_load_tool, transform_load_tool]

llm = llm_config()
llm_bind = llm.bind_tools(tools, tool_choice="auto")

#------------------------------------------------------------AGENT GRAPH ----------------------------------------------------------

def llm_node(state: ETLAgentSchema):
    
    messages = state.messages
    
    prompt = f"""
            You are a Python Data Analyst who has access to tools that can extract and load, 
            transform and load data. You will be provided with a user's question 
            and you would need to perform the right ETL operations as per the user's question. 
            If the operation is performed then inform the user and end the coversation.
            Here's the chat history: {messages}\n
    """
    final_answer = llm_bind.invoke(prompt) 
    
    state.messages = state.messages + [final_answer]
    
    return state

def tool_node(state: ETLAgentSchema):
    
    
    tools_result = []
    tools_by_name = {tool.name :tool for tool in tools}
    
    tool_calls = state.messages[-1].tool_calls
    #print(tool_calls)
    for tool_call in tool_calls:
        tool =  tools_by_name[tool_call['name']] 
        observation = tool.invoke(tool_call['args'])
        
        tools_result.append(ToolMessage(content = observation, tool_call_id= tool_call['id']))
        
    state.messages = state.messages + tools_result
    
    return state

#---------------------------------------------------AGENT GRAPH--------------------------------------

etl_analyst_graph = StateGraph(ETLAgentSchema)

#Nodes
etl_analyst_graph.add_node("llm_node", llm_node)
etl_analyst_graph.add_node("tool_node", tool_node)

#Edges
etl_analyst_graph.add_edge(START,"llm_node")

def is_tool_call(state: ETLAgentSchema):
    
    tool_call = state.messages[-1].tool_calls
    
    if tool_call:
        return "tool_node"
    else:
        return "end"
   
etl_analyst_graph.add_conditional_edges(
    "llm_node", is_tool_call,
    {
        "tool_node": "tool_node",
        "end": END
    })

etl_analyst_graph.add_edge("tool_node", "llm_node")


etl_analyst = etl_analyst_graph.compile()

if __name__ == "__main__":
    
    etl_analyst = etl_analyst_graph.compile()
    
    #response = etl_analyst.invoke(
    #    {
    #        "messages": [HumanMessage(content = "I want to extract the data from the API Endpoint 'https://pokeapi.co/api/v2/pokemon' and save it as csv file in the folder 'data/output'.")]
    #    }
    #)
    response = etl_analyst.invoke(
          {"messages":[HumanMessage(content="""
             I want to transform the data stored in the 'data/output/Extracted_data.csv' file 
             and save the transformed data in the 'data/transform' folder in the csv format.
             The transformation should filter the data to show bulbasaur pokemon only.
 """)]}
     ) 
    print(response)
    #from IPython.display import display,Image
    #img = Image(etl_analyst.get_graph().draw_mermaid_png())
    #with open("image.png","wb") as f:
    #   f.write(img.data)
        
#    llm_bind = llm_config().bind_tools(tools)
#    print(llm_bind.invoke("I want to extract the data from the API Endpoint 'https://api.example.com/data' and save it as csv file in the folder 'data/output'."))