from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()

def llm_config():
    
    llm = ChatGroq(model_name = "openai/gpt-oss-20b", temperature = 0)
    
    return llm

if __name__ =="__main__":
    llm_obj = llm_config()
    print(llm_obj.invoke("Write a python code to find even or odd. I need a code only").content)