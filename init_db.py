from intelligence_api.core.database import init_db, engine
from intelligence_api.domain.models import Base

if __name__ == "__main__":
    print("🚀 Initializing database (creating missing tables)...")
    try:
        # Base.metadata.drop_all(engine)  # REMOVED: This was too destructive!
        init_db()
        print("✅ Success! Database tables are up to date.")
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
