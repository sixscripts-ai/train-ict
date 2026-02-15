import os
import glob
import json
import csv
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

# --- CONFIGURATION ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))

# Prioritized directories to ingest
SOURCE_DIRS = [
    "data",                # content: json, sql
    "Collected_ICT_Data", # content: csv, md
    "knowledge_base",     # content: md
    "journal",            # content: md
    "docs",               # content: md
]

DB_PATH = os.path.join(PROJECT_ROOT, "ai_rag/rag_db")
MODEL_NAME = "llama3.2"
EMBEDDING_MODEL = "nomic-embed-text"

def load_json_file(file_path):
    """Parses a JSON file and converts it into a text document."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Convert JSON to a pretty string representation
        text_content = json.dumps(data, indent=2)
        return [Document(page_content=text_content, metadata={"source": file_path})]
    except Exception as e:
        print(f"Error loading JSON {file_path}: {e}")
        return []

def load_csv_file(file_path):
    """Parses a CSV file and creates a document for each row (trade)."""
    documents = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Create a readable summary of the trade row
                # We assume standard headers, but fallback to a dump
                content_parts = []
                for k, v in row.items():
                    if v: content_parts.append(f"{k}: {v}")
                
                text_content = "Trade Record:\n" + "\n".join(content_parts)
                documents.append(Document(page_content=text_content, metadata={"source": file_path}))
    except Exception as e:
        print(f"Error loading CSV {file_path}: {e}")
    return documents

def load_documents():
    documents = []
    print(f"Scanning project root: {PROJECT_ROOT}")
    
    for dir_name in SOURCE_DIRS:
        full_dir_path = os.path.join(PROJECT_ROOT, dir_name)
        if not os.path.exists(full_dir_path):
            print(f"Skipping {dir_name} (not found)")
            continue
            
        print(f"Scanning {dir_name}...")
        
        # Helper to check size
        def is_too_large(path):
            # Limit to 1MB to avoid massive dumps
            if os.path.getsize(path) > 1 * 1024 * 1024: 
                print(f"  Skipping {os.path.basename(path)} (too large: {os.path.getsize(path)/1024/1024:.2f} MB)")
                return True
            return False

        # 1. MARKDOWN FILES
        md_files = glob.glob(os.path.join(full_dir_path, "**/*.md"), recursive=True)
        for file_path in md_files:
            if is_too_large(file_path): continue
            try:
                loader = TextLoader(file_path, encoding='utf-8')
                loaded_docs = loader.load()
                for doc in loaded_docs:
                    doc.metadata['source_dir'] = dir_name
                    doc.metadata['filename'] = os.path.basename(file_path)
                documents.extend(loaded_docs)
            except Exception:
                pass

        # 2. JSON FILES
        json_files = glob.glob(os.path.join(full_dir_path, "**/*.json"), recursive=True)
        for file_path in json_files:
            if is_too_large(file_path): continue
            documents.extend(load_json_file(file_path))

        # 3. CSV FILES
        csv_files = glob.glob(os.path.join(full_dir_path, "**/*.csv"), recursive=True)
        for file_path in csv_files:
            if is_too_large(file_path): continue
            documents.extend(load_csv_file(file_path))
            
    print(f"Total documents loaded: {len(documents)}")
    return documents

def ingest():
    print("--- Starting Enhanced Ingestion ---")
    
    # 1. Load Data
    docs = load_documents()
    if not docs:
        print("No documents found.")
        return

    # 2. Split Text
    # We use a larger chunk size to keep full trade contexts together
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500, 
        chunk_overlap=300
    )
    chunks = text_splitter.split_documents(docs)
    print(f"Created {len(chunks)} chunks from {len(docs)} source documents.")

    # 3. Embed and Store
    print("Creating embeddings and storing in ChromaDB...")
    embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)
    
    # Initialize Chroma
    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=DB_PATH
    )
    print(f"--- Ingestion Complete! Database saved to {DB_PATH} ---")

if __name__ == "__main__":
    ingest()
