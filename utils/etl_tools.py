import os
import requests
import pandas as pd

class ETLTools:
    
    def __init__(self):
        
        pass
    
    def extract_load(self, url: str, output_folder: str, format: str):
        
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__),".."))
        output_folder = os.path.join(project_root, output_folder)
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            data =  response.json()
            
            file_name = os.path.join(output_folder, f"Extracted_data.{format}")
            os.makedirs(output_folder, exist_ok= True)
            
            df = pd.json_normalize(data)
            if format.lower() == "csv":
                df.to_csv(file_name, index=False)
            
            elif format.lower() == "json":
                df.to_json(file_name, orient="records", lines=True)
            
            elif format.lower() == "parquet":
                df.to_parquet(file_name, index=False)
            
            else:
                return f"Unsupported format: {format}"
            
            return f"Data sucessfully extracted and saved to {file_name}.{format}"
        
        except Exception as E:
            return f"Data can't be Extracted: {E}"

    
    def transform_load_context(self,file_path: str):
        
        file_extension = os.path.splitext(file_path)[1].lower()
        if file_extension == ".csv":
            df = pd.read_csv(file_path)
        elif file_extension == ".json":
            df = pd.read_json(file_path)
        elif file_extension == ".parquet":
            df = pd.read_parquet(file_path)
        else:
            return f"Unsupported file format:{file_extension}"

        top_3_rows = str(df.head(3))
        return top_3_rows
    
    def execute_code(self,code:str):
        try:
            exec(code)
            return "Code Executed Sucessfully"
        except Exception as E:
            return f"Failed to execute code: {E}"
    
if __name__ == "__main__":
    obj = ETLTools()
    print(obj.extract_load("https://pokeapi.co/api/v2/pokemon/", "data/extract", "csv"))
    sample_file = os.path.join(os.path.dirname(__file__), "..", "data", "payments.csv")
    print(obj.transform_load_context(sample_file))