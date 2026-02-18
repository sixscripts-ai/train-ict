
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ict_agent.database.turso_db import TursoDB

def reset_concepts_table():
    print("Connecting to Turso DB...")
    db = TursoDB()
    
    print("Dropping 'ict_concepts' table...")
    try:
        db.execute("DROP TABLE ict_concepts")
        print("Table 'ict_concepts' dropped successfully.")
    except Exception as e:
        print(f"Error dropping table (might not exist): {e}")

    print("Re-initializing tables (creating new schema)...")
    try:
        db.initialize_tables()
        print("Tables initialized successfully with correct schema.")
    except Exception as e:
        print(f"Error initializing tables: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    reset_concepts_table()
