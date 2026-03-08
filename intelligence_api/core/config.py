import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://dev:dev_password@localhost:5432/omnisight_local")
    PROJECT_ID: str = os.getenv("PROJECT_ID", "omnisight-project")
    PUBSUB_TOPIC: str = "raw-events"
    PUBSUB_TOPIC_PATH: Optional[str] = None
    
    AZURE_OPENAI_API_KEY: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    AZURE_OPENAI_ENDPOINT: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    AZURE_EMBEDDING_DEPLOYMENT: str = os.getenv("AZURE_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")
    AZURE_CHAT_DEPLOYMENT: str = os.getenv("AZURE_CHAT_DEPLOYMENT", "gpt-4o-mini")
    
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")
    PINECONE_INDEX: str = "omnisight-cache"
    
    # --- Market Data ---
    TWELVE_DATA_API_KEY: Optional[str] = os.getenv("TWELVE_DATA_API_KEY")
    
    # --- Scrapers ---
    REDDIT_CLIENT_ID: Optional[str] = os.getenv("REDDIT_CLIENT_ID")
    REDDIT_CLIENT_SECRET: Optional[str] = os.getenv("REDDIT_CLIENT_SECRET")
    NITTER_INSTANCE: str = os.getenv("NITTER_INSTANCE", "https://nitter.net")

    # --- Auth ---
    # Must match NEXTAUTH_SECRET in the Next.js frontend .env.local
    NEXTAUTH_SECRET: str = os.getenv("NEXTAUTH_SECRET", "change-me-in-production")
    # Allowed CORS origins (comma-separated for multiple)
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
    
    model_config = {
        "env_file": ".env",
        "extra": "ignore"  # Allow extra fields in .env without crashing
    }

settings = Settings()
