from intelligence_api.core.database import init_db, engine
from intelligence_api.domain.models import Base

if __name__ == "__main__":
    print("🚀 Re-initializing database (dropping and creating all tables)...")
    try:
        Base.metadata.drop_all(engine)
        init_db()
        print("✅ Success! Tables 'entities', 'events', and 'daily_trends' have been refreshed.")
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
