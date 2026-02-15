---
description: Setup a free local RAG system to chat with your ICT trading data
---

# Setup Local RAG for ICT Data

This workflow sets up a local, free RAG (Retrieval-Augmented Generation) system using **Ollama** and **ChromaDB**. This allows you to chat with your trading logs, journals, and Markdown documentation without sending data to the cloud.

This setup is the first step towards training a custom model. The interactions you have with this system can be saved to train a fine-tuned model later.

## Prerequisites

1.  **Ollama**: managing local LLMs.
    -   Download from [ollama.com](https://ollama.com) and install it.
    -   Ensure it is running (you should see the icon in your menu bar).
2.  **Python 3**: Ensure Python is installed.

## Step 1: Prepare the Environment

Open your terminal in the project root (`ict_trainer`).

1.  **Pull the AI Model**: We will use `llama3.2` (3B parameters) as it is fast and efficient for local use.
    ```zsh
    ollama pull llama3.2
    ```

2.  **Create a Virtual Environment**:
    ```zsh
    python3 -m venv venv_rag
    source venv_rag/bin/activate
    ```

3.  **Install Python Libraries**:
    We need LangChain (for orchestration), ChromaDB (database), and the Ollama connector.
    ```zsh
    pip install langchain langchain-community langchain-ollama chromadb sentence-transformers
    ```

## Step 2: Create the Ingestion Script

This script reads your Markdown files and indexes them into the vector database.

Create a file at `scripts/rag_ingest.py`:

```python
import os
import glob
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import Chroma

# --- CONFIGURATION ---
# Adjust this path to where your markdown files are located
DOCS_PATH = "./docs" 
DB_PATH = "./rag_db"
MODEL_NAME = "llama3.2"

def load_documents():
    documents = []
    # Find all markdown files recursively
    files = glob.glob(os.path.join(DOCS_PATH, "**/*.md"), recursive=True)
    
    print(f"Found {len(files)} markdown files in {DOCS_PATH}")
    
    for file_path in files:
        try:
            loader = TextLoader(file_path, encoding='utf-8')
            documents.extend(loader.load())
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            
    return documents

def ingest():
    print("--- Starting Ingestion ---")
    
    # 1. Load Data
    docs = load_documents()
    if not docs:
        print("No documents found. Check your DOCS_PATH.")
        return

    # 2. Split Text (Chunks)
    # ICT concepts can be complex, so we keep chunks larger with overlap
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200, 
        chunk_overlap=300
    )
    chunks = text_splitter.split_documents(docs)
    print(f"Created {len(chunks)} chunks from {len(docs)} documents.")

    # 3. Embed and Store
    print("Creating embeddings and storing in ChromaDB...")
    embeddings = OllamaEmbeddings(model=MODEL_NAME)
    
    # Remove old DB if you want a fresh start, or just append
    if os.path.exists(DB_PATH):
        print(f"Updating existing database at {DB_PATH}")
    
    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=DB_PATH
    )
    print("--- Ingestion Complete! ---")

if __name__ == "__main__":
    ingest()
```

## Step 3: Create the Chat Script

This script lets you talk to your data.

Create a file at `scripts/rag_chat.py`:

```python
import argparse
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_ollama import ChatOllama
from langchain.prompts import ChatPromptTemplate

# --- CONFIGURATION ---
DB_PATH = "./rag_db"
MODEL_NAME = "llama3.2"

# ICT Persona Prompt
PROMPT_TEMPLATE = """
You are an expert ICT (Inner Circle Trader) mentor.
Use the following pieces of context from the user's personal trading journals and notes to answer the question.
If the answer is not in the context, say you don't know, but try to infer from general ICT knowledge if applicable, while prioritizing the user's specific notes.

Context:
{context}

---

Question: {question}
"""

def chat_loop():
    print("Initializing ICT Mentor with Local Data...")
    
    embeddings = OllamaEmbeddings(model=MODEL_NAME)
    db = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)
    model = ChatOllama(model=MODEL_NAME)
    prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    
    chain = prompt | model

    print("\n✅ System Ready. Ask questions about your trades (type 'exit' to quit).\n")

    while True:
        query_text = input("You: ")
        if query_text.lower() in ['exit', 'quit', 'q']:
            break
            
        # 1. Search DB
        results = db.similarity_search_with_score(query_text, k=5)
        
        # 2. Prepare Context
        context_text = "\n\n---\n\n".join([doc.page_content for doc, _score in results])
        
        # 3. Generate Answer
        print("\nMentor: Thinking...")
        response = chain.invoke({"context": context_text, "question": query_text})
        
        print(f"\n{response.content}\n")
        print("-" * 50)

if __name__ == "__main__":
    chat_loop()
```

## Step 4: Run It

1.  **Ingest Data**:
    ```zsh
    python3 scripts/rag_ingest.py
    ```
2.  **Chat**:
    ```zsh
    python3 scripts/rag_chat.py
    ```

## Future: Preparing for Fine-Tuning

To eventually fine-tune a model (Method #2), you will modify `scripts/rag_chat.py` to auto-save good Q&A pairs to a JSON file. 
