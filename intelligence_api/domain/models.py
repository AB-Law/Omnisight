import uuid
from sqlalchemy import Column, String, Boolean, JSON, Numeric, DateTime, ForeignKey, Date, Text, UniqueConstraint, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class Entity(Base):
    __tablename__ = "entities"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    label = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)  # 'COMPANY', 'USER'
    is_pii = Column(Boolean, default=False)
    sector = Column(String(100), nullable=True)       # e.g. 'Technology', 'Finance'
    description = Column(Text, nullable=True)          # Brief company/entity description from AI
    metadata_json = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ScrapedEvent(Base):
    __tablename__ = "events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.id"))
    source_type = Column(String(50))  # 'REDDIT', 'RSS', 'NITTER'
    content = Column(Text, nullable=False)
    cleaned_content = Column(Text)
    sentiment_score = Column(Numeric(3, 2))
    summary = Column(Text)
    category = Column(String(100))
    raw_url = Column(Text)
    published_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class DailyTrend(Base):
    __tablename__ = "daily_trends"
    
    entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.id"), primary_key=True)
    observation_date = Column(Date, primary_key=True)
    avg_sentiment = Column(Numeric(5, 4))
    event_count = Column(Integer, default=0)
    volume = Column(JSON) # Aggregated metric details

class ScrapeTarget(Base):
    __tablename__ = "scrape_targets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    target_name = Column(String(255), nullable=False)
    source_type = Column(String(50), nullable=False) # 'REDDIT', 'NITTER', 'NEWS'
    scrape_interval_minutes = Column(Numeric, nullable=False, default=60) # Interval for scheduler
    campaign = Column(String(255), nullable=True) # E.g. 'Competitor Intel'
    
    status = Column(String(50), default="Pending") # 'Pending', 'Running', 'Completed', 'Error'
    error_message = Column(Text, nullable=True)
    
    metadata_json = Column(JSON, default={}, nullable=True) # For scraper-specific params like 'period'
    
    last_scraped_at = Column(DateTime(timezone=True), nullable=True)
    next_scrape_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class TickerMapping(Base):
    """Cache: company name → ticker symbol, with error tracking"""
    __tablename__ = "ticker_mappings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_name = Column(String(255), unique=True, nullable=False, index=True)
    ticker_symbol = Column(String(20), nullable=True)    # None if resolution failed
    exchange = Column(String(50), nullable=True)          # e.g. 'NASDAQ'
    resolved_via = Column(String(50), nullable=True)      # 'yfinance' | 'twelvedata'
    status = Column(String(50), default="resolved")       # 'resolved' | 'failed'
    error_message = Column(Text, nullable=True)           # Why resolution failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class StockPrice(Base):
    """Daily OHLCV prices per ticker"""
    __tablename__ = "stock_prices"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticker_symbol = Column(String(20), nullable=False, index=True)
    date = Column(Date, nullable=False)
    open = Column(Numeric(12, 4))
    high = Column(Numeric(12, 4))
    low = Column(Numeric(12, 4))
    close = Column(Numeric(12, 4))
    volume = Column(Numeric(20, 0))
    
    __table_args__ = (
        UniqueConstraint('ticker_symbol', 'date', name='uq_ticker_date'),
    )
