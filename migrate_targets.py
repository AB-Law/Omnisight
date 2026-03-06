from sqlalchemy import text
from intelligence_api.core.database import engine

def migrate():
    print("🚀 Running migrations...")
    try:
        with engine.connect() as conn:
            # Check if table exists
            result = conn.execute(text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'scrape_targets');"))
            exists = result.scalar()
            
            if not exists:
                print("🛠️ Creating 'scrape_targets' table...")
                conn.execute(text("""
                CREATE TABLE scrape_targets (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    target_name VARCHAR(255) NOT NULL,
                    source_type VARCHAR(50) NOT NULL,
                    scrape_interval_minutes NUMERIC NOT NULL DEFAULT 60,
                    campaign VARCHAR(255),
                    status VARCHAR(50) DEFAULT 'Pending',
                    error_message TEXT,
                    last_scraped_at TIMESTAMP WITH TIME ZONE,
                    next_scrape_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
                """))
                conn.commit()
                print("✅ 'scrape_targets' table created successfully.")
            else:
                print("✅ 'scrape_targets' table already exists. No migration needed.")
    except Exception as e:
        print(f"❌ Migration failed: {e}")

if __name__ == "__main__":
    migrate()
