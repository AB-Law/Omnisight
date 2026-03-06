import sys
import os

# Add the project root to sys.path so we can import internal modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from intelligence_api.core.database import engine
from intelligence_api.domain.models import Base
from intelligence_api.core.config import settings
import pinecone
from sqlalchemy import text

def wipe_relational_db():
    print("🗑️ Wiping relational database tables...")
    try:
        with engine.connect() as conn:
            # We use TRUNCATE with CASCADE to clear all data while keeping the schema
            # Order matters less with CASCADE, but let's be thorough
            tables = [
                "entity_relationships",
                "entity_mentions",
                "events",
                "daily_trends",
                "entities",
                "scrape_targets",
                "ticker_mappings",
                "stock_prices"
            ]
            
            for table in tables:
                print(f"  - Truncating {table}...")
                conn.execute(text(f"TRUNCATE TABLE {table} CASCADE;"))
            
            conn.commit()
            print("✅ Relational database wiped.")
    except Exception as e:
        print(f"❌ Error wiping relational DB: {e}")

def wipe_pinecone():
    print("🗑️ Clearing Pinecone semantic cache...")
    try:
        pc = pinecone.Pinecone(api_key=settings.PINECONE_API_KEY)
        index = pc.Index(settings.PINECONE_INDEX)
        # Delete all vectors in the index
        index.delete(delete_all=True)
        print("✅ Pinecone cache cleared.")
    except Exception as e:
        print(f"❌ Error clearing Pinecone: {e}")

if __name__ == "__main__":
    confirm = input("ARE YOU SURE you want to delete EVERYTHING from the DB and Cache? (y/n): ")
    if confirm.lower() == 'y':
        wipe_relational_db()
        wipe_pinecone()
        print("\n✨ Omnisight has been reset to a clean state.")
    else:
        print("Operation cancelled.")
