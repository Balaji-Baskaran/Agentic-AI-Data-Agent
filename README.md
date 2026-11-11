# Data Agent 🤖📊

An intelligent, multi-agent data assistant built with **LangGraph**, **Groq LLM**, **PostgreSQL**, and **Pandas**.

The Data Agent autonomously routes user questions to specialized sub-agents:
- **SQL Analyst Agent**: Converts natural language into PostgreSQL queries, evaluates query safety via an LLM judge, executes read-only queries, and summarizes the results in plain English.
- **ETL Analyst Agent**: Fetches data from external REST APIs (CSV, JSON, Parquet) and applies Pandas-based transformations.

---

## Architecture Overview

```
                          ┌─────────────────────┐
                          │     User Query      │
                          └──────────┬──────────┘
                                     │
                                     ▼
                          ┌─────────────────────┐
                          │     Router Node     │
                          └────┬───────────┬────┘
                               │           │
                       "SQL"   │           │   "ETL"
                               ▼           ▼
       ┌────────────────────────┐         ┌────────────────────────┐
       │   SQL Analyst Graph    │         │   ETL Analyst Graph    │
       │                        │         │                        │
       │  • Curate Question     │         │  • extract_load_tool   │
       │  • Schema Inspection   │         │  • transform_load_tool │
       │  • SQL Generation      │         │  • Dynamic Pandas Exec │
       │  • Safety Judge Check  │         │                        │
       │  • Execution & Answer  │         └────────────────────────┘
       └────────────────────────┘
```

---

## Features

- **Intelligent Intent Routing**: Routes incoming requests between SQL analytical queries and ETL pipelines based on structured LLM classification.
- **Automated Schema Discovery**: Inspects PostgreSQL database schema (`information_schema`) and samples top rows dynamically to construct high-accuracy context prompts.
- **SQL Safety Guardrail**: An LLM-powered judge evaluates generated SQL queries before execution, blocking destructive commands (`DROP`, `DELETE`, `UPDATE`, `ALTER`, `TRUNCATE`, `CREATE`).
- **Flexible ETL Pipelines**: Ingests data from arbitrary REST APIs and saves into CSV, JSON, or Parquet formats, with automated code generation for data manipulation.

---


## Getting Started

### 1. Prerequisites
- **Python 3.12+**
- **PostgreSQL** running locally or remotely
- [**uv**](https://github.com/astral-sh/uv) (recommended) or standard `pip`
- A [**Groq API Key**](https://console.groq.com/)

### 2. Clone the Repository
```bash
git clone https://github.com/Balaji-Baskaran/data-agent.git
cd data-agent
```

### 3. Configure Environment Variables
Copy the example environment file and fill in your credentials:
```bash
cp .env.example .env
```

Edit `.env`:
```ini
GROQ_API_KEY=gsk_your_groq_api_key_here

database=postgres
host=localhost
port=5432
user=postgres
password=your_db_password_here
```

### 4. Install Dependencies
Using **uv**:
```bash
uv sync
```
Or using **pip**:
```bash
pip install -e .
```

### 5. Seed the Database
Ensure your PostgreSQL server is running, then run the database setup script to create tables and load sample ride-sharing data:
```bash
python feed_data.py
```

---

## Usage

Start the interactive Data Agent CLI:
```bash
python main.py
```

### Example Queries

#### SQL Analytical Queries:
- *"What are the different types of vehicles we have in our database?"*
- *"Show the top 5 riders with the highest number of completed rides."*
- *"What is the total revenue collected per city in the payments table?"*

#### ETL Data Operations:
- *"Extract the data from API endpoint 'https://pokeapi.co/api/v2/pokemon' and save it as a CSV in data/output."*
- *"Transform data in 'data/output/Extracted_data.csv' and filter records where status is active, saving to data/transform."*

---

