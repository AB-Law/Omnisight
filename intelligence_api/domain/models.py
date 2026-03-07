import uuid
from sqlalchemy import Column, String, Boolean, JSON, Numeric, DateTime, ForeignKey, Date, Text, UniqueConstraint, Integer, Index
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


# ──────────────── Knowledge Graph Tables ────────────────

ENTITY_MENTION_TYPES = ('PERSON', 'COMPANY', 'ORG', 'LOCATION', 'PRODUCT', 'TOPIC')


class EntityMention(Base):
    """Every named entity extracted from a scraped event by the LLM."""
    __tablename__ = "entity_mentions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    mentioned_name = Column(String(255), nullable=False)          # Raw extracted name (e.g. "Elon Musk")
    mentioned_type = Column(String(50), nullable=False)           # PERSON, COMPANY, ORG, LOCATION, PRODUCT, TOPIC
    resolved_entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.id", ondelete="SET NULL"), nullable=True)  # Matched to a tracked Entity
    confidence = Column(Numeric(3, 2), nullable=True)             # LLM confidence score (0-1), for future quality filtering
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('ix_entity_mentions_name_type', 'mentioned_name', 'mentioned_type'),
    )


class EntityRelationship(Base):
    """Pre-computed co-occurrence edges between entity pairs. 
    
    Canonical ordering: entity_a_name < entity_b_name (lexicographic) to prevent duplicate edges.
    Updated incrementally on each event that co-mentions the pair.
    """
    __tablename__ = "entity_relationships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_a_name = Column(String(255), nullable=False)           # Always the lexicographically smaller name
    entity_b_name = Column(String(255), nullable=False)           # Always the lexicographically larger name
    entity_a_type = Column(String(50), nullable=True)             # Used for graph node color-coding
    entity_b_type = Column(String(50), nullable=True)
    co_occurrence_count = Column(Integer, default=1, nullable=False)  # How many events mention both
    avg_sentiment = Column(Numeric(5, 4), nullable=True)          # Avg sentiment across shared events
    first_seen = Column(DateTime(timezone=True), server_default=func.now())
    last_seen = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    source_types = Column(JSON, default={})                       # e.g. {"Reddit": 3, "Google News": 8}

    __table_args__ = (
        UniqueConstraint('entity_a_name', 'entity_b_name', name='uq_entity_relationship_pair'),
        Index('ix_entity_relationships_a', 'entity_a_name'),
        Index('ix_entity_relationships_b', 'entity_b_name'),
    )


# ──────────────── Chat / Conversation Tables ────────────────

class ConversationSession(Base):
    """A persistent chat session. One session = one conversation thread."""
    __tablename__ = "conversation_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=True)          # Auto-generated from first message
    entity_focus = Column(String(255), nullable=True)   # Optional: primary entity the session is about
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ConversationMessage(Base):
    """A single message within a conversation session."""
    __tablename__ = "conversation_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("conversation_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)            # 'user' | 'assistant' | 'tool'
    content = Column(Text, nullable=True)               # Text content (may be empty for pure tool messages)
    tool_name = Column(String(100), nullable=True)      # Set when role='tool'
    tool_call_id = Column(String(100), nullable=True)   # OpenAI tool_call_id for correlation
    tool_args = Column(JSON, nullable=True)             # Arguments passed to the tool
    tool_result = Column(JSON, nullable=True)           # Structured result from the tool (including viz data)
    metadata_json = Column(JSON, default={})            # e.g. {"confidence": 0.94, "sources": [...]}
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('ix_conversation_messages_session', 'session_id', 'created_at'),
    )
