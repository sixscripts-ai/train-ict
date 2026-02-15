import argparse
import os
import sys
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_ollama import ChatOllama
from langchain.prompts import ChatPromptTemplate

# --- CONFIGURATION ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
DB_PATH = os.path.join(PROJECT_ROOT, "ai_rag/rag_db")
MODEL_NAME = "llama3.2"
EMBEDDING_MODEL = "nomic-embed-text"

# ICT Persona Prompt
PROMPT_TEMPLATE = """
You are an expert ICT (Inner Circle Trader) mentor. 
Your goal is to help the user improve their trading by recalling their own past trades, journals, and notes.

Use the following pieces of context from the user's personal trading data to answer the question.
If the answer is NOT in the context, say "I don't see anything about that in your notes," then offer general ICT advice if relevant.
ALWAYS cite the source file if possible (e.g., "In your journal from Jan 20th...").

Context:
{context}

---

Question: {question}
"""

def chat_loop():
    print(f"Initializing ICT Mentor with Local Data from: {DB_PATH}")
    
    if not os.path.exists(DB_PATH):
        print("Error: Database not found. Please run 'rag_ingest.py' first.")
        return

    # Use dedicated embedding model for retrieval
    embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)
    db = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)
    model = ChatOllama(model=MODEL_NAME)
    prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    
    chain = prompt | model

    print("\n✅ System Ready. Ask questions about your trades (type 'exit' to quit).\n")

    while True:
        try:
            query_text = input("You: ")
            if query_text.lower() in ['exit', 'quit', 'q']:
                break
            if not query_text.strip():
                continue
                
            # 1. Search DB
            results = db.similarity_search_with_score(query_text, k=5)
            
            # 2. Prepare Context
            context_pieces = []
            for doc, _score in results:
                # Include source filename in the context so the AI can cite it
                source = doc.metadata.get('filename', 'unknown file')
                content = doc.page_content
                context_pieces.append(f"[Source: {source}]\n{content}")
            
            context_text = "\n\n---\n\n".join(context_pieces)
            
            # 3. Generate Answer
            print("\nMentor: Thinking...", end="", flush=True)
            response = chain.invoke({"context": context_text, "question": query_text})
            
            # Clear "Thinking..." line
            print("\r" + " " * 20 + "\r", end="")
            
            print(f"Mentor: {response.content}\n")
            print("-" * 50)
        except KeyboardInterrupt:
             print("\nExiting...")
             break
        except Exception as e:
            print(f"\nError: {e}")

if __name__ == "__main__":
    chat_loop()
