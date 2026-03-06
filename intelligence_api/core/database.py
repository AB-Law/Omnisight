from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from intelligence_api.core.config import settings
from intelligence_api.domain.models import Base

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
