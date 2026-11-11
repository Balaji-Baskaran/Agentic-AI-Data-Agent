import os
import sys
from dotenv import load_dotenv
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.llm_config import llm_config
from utils.database import DatabaseUtils
from models.schema import AgentSchema,JudgeSchema
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
load_dotenv()


#-------------------------------------------------- AI Agent --------------------------------------

#Curate a user prompt
def curate_question(state: AgentSchema) -> AgentSchema:
    
    user_question = state.user_question
    
    llm = llm_config()
    
    response = llm.invoke(f"Curate the following question so that we can use it : {user_question}").content
    
    state.curated_user_prompt = response
    state.messages = state.messages + [HumanMessage(content=f"{response}")]
    
    return state

#Generate a SQL context prompt
def prompt_query_context(state: AgentSchema) -> AgentSchema:
    
    curated_question = state.curated_user_prompt
    
    conn_details = {
        "host": os.environ["host"],
        "port": int(os.environ["port"]),
        "database": os.environ["database"],
        "user": os.environ["user"],
        "password": os.environ["password"]
    }
    
    db_obj  = DatabaseUtils(conn_details)
    
    schema_info = db_obj.schema_details("public")
    
    prompt = f"""
    You are an SQL analyst agent. Your task is to convert the user's natural language 
    query into Postgres SQL query that can be executed on the database. You are provided 
    with the user's original query and the schema details of the database, including
    table names, column names, data types, and sample data for each table so that 
    you can understand the structure of the database and generate an accurate SQL query.
    Unless user explicitly asks for specific number of rows, always limit the output to 10 rows.
    Note - Just generate the SQL query without any explanation or additional text because
    this query will be executed directly on the database. So, the output should be SQL
    ready to be executed without any modifications.  
    
    User's Original Query: {curated_question}

    Database Schema Details:
    {schema_info}
    
    """   
     
    state.prompt_query_context = prompt
    
    
    
    return state

#Generate SQL Query
def generate_sql_query(state: AgentSchema) -> AgentSchema:
    
    prompt = state.prompt_query_context
    
    llm = llm_config()
    generated_sql_query = llm.invoke(prompt).content

    state.generated_sql_query = generated_sql_query
    
    return state


#Check SQL Query is safe or not
def is_safe_query(state: AgentSchema) -> AgentSchema:
    
    sql_query = state.generated_sql_query
    
    llm = llm_config()
    llm_judge = llm.with_structured_output(JudgeSchema)
    
    prompt = f"""
    You are an SQL analyst Judge for data security.
    Your task is to determine the SQL query is safe or not. 
    The SQL query is only used for data retrieval and should not modify the database in any way. 
    Neither the SQL query nor the prompt should contain any SQL commands that can modify the database, 
    such as INSERT, DELETE, UPDATE, DROP, ALTER, TRUNCATE, CREATE or any commands that can change the 
    structure or content of the database. If the SQL query is safe, respond with "Yes"  otherwise respond with "No".
    Additionally, provide comments explaining your decision.
    Here's the SQL query to evaluate:
    {sql_query}
    """

    response = llm_judge.invoke(prompt).model_dump()
    
    state.is_safe = response['answer']
    state.comment = response.get('comment', '')
    
    return state

#Cancelled SQL query
def cancel_sql(state: AgentSchema) -> AgentSchema:
    
    comment = state.comment
    
    state.final_answer =  f"The generated Sql Query was deemed unsafe to execute. The reason provide by the judge is: {comment}"
    state.messages = state.messages + [AIMessage(content= state.final_answer)]
    
    return state


#Executing SQL query
def execute_sql(state: AgentSchema) -> AgentSchema:
    
    sql_query = state.generated_sql_query
    
    conn_details = {
        "host": os.environ["host"],
        "port": os.environ["port"],
        "database": os.environ["database"],
        "user": os.environ["user"],
        "password": os.environ["password"]
    }
    
    obj = DatabaseUtils(conn_details)
    execution_result = obj.execute_sql(sql_query)
    
    state.sql_query_execution_result = execution_result
    
    return state


#Representation Node Final Node
def represent_final_answer(state: AgentSchema) -> AgentSchema:
    
    execution_result = state.sql_query_execution_result
    curated_question = state.curated_user_prompt
    
    llm = llm_config()
    
    prompt = f"""
    You are an SQL analyst agent. Your task is to provide a final answer to the user based on the
    execution result of the SQL query and the user's original question. The final answer should be
    concise, clear and directly address the user's query. Avoid including any SQL code or technical
    details in the final answer. The final answer should be in a user-friendly format that is easy to
    understand. If the execution result is empty or does not provide a clear answer to the user's question.
    Explain this in final answer\n
    Here is the execution result: {execution_result}\n
    Here is the users original question: {curated_question}
    """
    response = llm.invoke(prompt).content
    state.final_answer = response
    state.messages = state.messages + [AIMessage(content = response)]
    
    return state


# ------------------------------------------ Graph Building ----------------------------------
sql_agent_graph = StateGraph(AgentSchema)

sql_agent_graph.add_node(curate_question, name = "curate_question")
sql_agent_graph.add_node(prompt_query_context, name= "prompt_query_context")
sql_agent_graph.add_node(generate_sql_query, name= "generate_sql_query")
sql_agent_graph.add_node(is_safe_query, name="is_safe_query")
sql_agent_graph.add_node(cancel_sql, name="cancel_sql")
sql_agent_graph.add_node(execute_sql, name="execute_sql")
sql_agent_graph.add_node(represent_final_answer, name="represent_final_answer")

#Edges
sql_agent_graph.add_edge(START, "curate_question")
sql_agent_graph.add_edge("curate_question", "prompt_query_context")
sql_agent_graph.add_edge("prompt_query_context", "generate_sql_query")
sql_agent_graph.add_edge("generate_sql_query", "is_safe_query")

#conditional edge function
def is_safe_sql_edge(state: AgentSchema) -> str:
    
    is_safe = state.is_safe
    
    if is_safe.lower() == "yes":
        return "execute_sql"
    else:
        return "cancel_sql"


sql_agent_graph.add_conditional_edges("is_safe_query", is_safe_sql_edge,
                                      {
                                          "execute_sql": "execute_sql",
                                          "cancel_sql" : "cancel_sql"
                                      })
sql_agent_graph.add_edge("cancel_sql", END)
sql_agent_graph.add_edge("execute_sql", "represent_final_answer")
sql_agent_graph.add_edge("represent_final_answer", END)

#Compile the Graph
sql_analyst = sql_agent_graph.compile()
if __name__ == "__main__":  

    #from IPython.display import Image
    #img = Image(sql_analyst.get_graph().draw_mermaid_png())
    #with open("image.png","wb") as f:
    #   f.write(img.data)
    
    input_schema = {
        "messages": [],
        "user_question": "What are the different types of vehicle we have in our database ",
        "curated_user_prompt": " ",
        "prompt_query_context": " ",
        "generated_sql_query": " ",
        "sql_query_execution_result": "",
        "is_safe" : "No",
        "comment": "",  
        "final_answer": " "
    }
    
    sql_analyst_response = sql_analyst.invoke(input_schema)
    print(sql_analyst_response['final_answer'])