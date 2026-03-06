from sqlalchemy import create_engine
from intelligence_api.core.config import settings
from intelligence_api.domain.models import Base

def reset_db():
    engine = create_engine(settings.DATABASE_URL)
    print("🗑️ Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("✨ Creating all tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database reset complete.")

if __name__ == "__main__":
    reset_db()
