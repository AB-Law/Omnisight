from typing import Dict, Any, Optional
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func
from intelligence_api.domain.models import Entity, ScrapedEvent, DailyTrend
from intelligence_api.infrastructure.ai_service import SemanticCache, AIClient
from intelligence_api.core.security import hash_pii, clean_content

class IntelligenceProcessor:
    def __init__(self, db: Session):
        self.db = db
        self.cache = SemanticCache()
        self.ai = AIClient()

    async def process_event(self, raw_data: Dict[str, Any]):
        content = raw_data.get("content", "")
        entity_label = raw_data.get("entity_label", "")
        source_type = raw_data.get("source_type", "")
        is_user = raw_data.get("is_user", False)

        # 1. PII Handling
        safe_label = hash_pii(entity_label) if is_user else entity_label
        sanitized_content = clean_content(content)
        
        # Parse published_at
        published_at_raw = raw_data.get("published_at")
        published_at = None
        if published_at_raw:
            try:
                if isinstance(published_at_raw, (int, float)):
                    from datetime import datetime, timezone
                    published_at = datetime.fromtimestamp(published_at_raw, tz=timezone.utc)
                else:
                    from dateutil import parser
                    published_at = parser.parse(str(published_at_raw))
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Could not parse published_at: {e}")

        # 2. Embedding
        embedding = self.ai.get_embedding(sanitized_content)

        # 3. Semantic Cache Check
        analysis = self.cache.check_cache(embedding)
        
        if not analysis:
            # 4. LLM Analysis (Cache Miss)
            analysis = self.ai.analyze_content(sanitized_content)
            
            # Tag the analysis with the entity label for future targeted deletion
            analysis_to_cache = analysis.copy()
            analysis_to_cache["entity_label"] = safe_label
            
            # Store in cache
            self.cache.store(sanitized_content, embedding, analysis_to_cache)


        # 5. DB Persistence
        # Ensure entity exists
        entity = self.db.query(Entity).filter(Entity.label == safe_label).first()
        if not entity:
            entity = Entity(
                label=safe_label, 
                type='USER' if is_user else 'COMPANY',
                is_pii=is_user,
                sector=analysis.get("sector"),
                description=analysis.get("entity_description")
            )
            self.db.add(entity)
            self.db.commit()
            self.db.refresh(entity)
        else:
            # Enrich existing entity with sector/description if missing
            updated = False
            if not entity.sector and analysis.get("sector") and analysis["sector"] != "Unknown":
                entity.sector = analysis["sector"]
                updated = True
            if not entity.description and analysis.get("entity_description"):
                entity.description = analysis["entity_description"]
                updated = True
            if updated:
                self.db.commit()

        event = ScrapedEvent(
            entity_id=entity.id,
            source_type=source_type,
            content=content,           # Original raw content
            cleaned_content=sanitized_content, # Cleaned/Sanitized content
            sentiment_score=analysis.get("sentiment"),
            summary=analysis.get("summary"),
            category=analysis.get("category"),
            raw_url=raw_data.get("raw_url"),
            published_at=published_at
        )
        self.db.add(event)
        self.db.commit()

        # 6. Populate DailyTrend (upsert for today's aggregation)
        self._update_daily_trend(entity.id, published_at)

        return analysis

    def _update_daily_trend(self, entity_id, published_at=None):
        """Upsert the DailyTrend row for this entity + date."""
        trend_date = published_at.date() if published_at else date.today()
        
        # Calculate fresh aggregation from events
        from sqlalchemy import cast, Date as SqlDate
        day_events = self.db.query(
            sa_func.avg(ScrapedEvent.sentiment_score),
            sa_func.count(ScrapedEvent.id)
        ).filter(
            ScrapedEvent.entity_id == entity_id,
            cast(ScrapedEvent.published_at, SqlDate) == trend_date
        ).first()
        
        avg_sent = float(day_events[0]) if day_events[0] is not None else 0.0
        count = day_events[1] or 0
        
        existing = self.db.query(DailyTrend).filter(
            DailyTrend.entity_id == entity_id,
            DailyTrend.observation_date == trend_date
        ).first()
        
        if existing:
            existing.avg_sentiment = avg_sent
            existing.event_count = count
        else:
            trend = DailyTrend(
                entity_id=entity_id,
                observation_date=trend_date,
                avg_sentiment=avg_sent,
                event_count=count
            )
            self.db.add(trend)
        
        self.db.commit()
