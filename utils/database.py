import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

class  DatabaseUtils:
    
    def __init__(self, db_config):
        
        self.db_config = db_config
        try:
            self.connection = psycopg2.connect(**db_config)
        except Exception as E:
            print(f"Database Connection Error: {E}")
            self.connection = None

    def schema_details(self, schema_name):
        
        try:
            schema_info_context = ""
            
            connection = self.connection
            cursor = connection.cursor()
            
            schema_info_context = f"Database Schema: {schema_name}\n"
            
            cursor.execute("SELECT table_name from information_schema.tables where table_schema = %s;", (schema_name,))
            table_list = cursor.fetchall()
            
            for table in table_list:
                
                table_name = table[0]
                schema_info_context = f"{schema_info_context}\nTable: {table_name}"
                
                cursor.execute("SELECT column_name, data_type from information_schema.columns where table_name = %s",(table_name,))
                column_list = cursor.fetchall()
                
                for column in column_list:
                    
                    column_name = column[0]
                    data_type = column[1]
                    
                    schema_info_context = f"{schema_info_context}\n     Column:{column_name}, Data Type:{data_type}"
            
            
                cursor.execute(f"Select * from {schema_name}.{table_name} limit 5")
                sample_data = cursor.fetchall()
                
                schema_info_context = f"{schema_info_context}\nSample Data:\n"
                
                for row in sample_data:
                    schema_info_context = f"{schema_info_context}      {row}\n"
                    
        except Exception as E:
            print(f"Error on fetching schema details: {E}")
            schema_info_context = f"Error fetching schema details: {E}"    
        
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
        
        return schema_info_context
    
    def execute_sql(self, query):
        
        connection = self.connection
        cursor = connection.cursor()
        
        try:
            cursor.execute(query)
            result = cursor.fetchall()
            
            connection.commit()
            
            return str(result)
        
        except Exception as E:
            return f"Data from the Database can't be retrieval:{E}"
        
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close() 
        
if __name__ == "__main__":
    table_context = DatabaseUtils({
        "host": os.getenv("host"),
        "port": os.getenv("port"),
        "database": os.getenv("database"),
        "user": os.getenv("user"),
        "password": os.getenv("password")
    })

    result = table_context.schema_details("public")

    with open("Schema_Entries_Through_Object.txt", "w") as file:
        file.write(result)

    