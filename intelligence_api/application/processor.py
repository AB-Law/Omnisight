from typing import Dict, Any, Optional, List
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func
from intelligence_api.domain.models import Entity, ScrapedEvent, DailyTrend, EntityMention, EntityRelationship
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

        # 5. DB Persistence — Ensure entity exists
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
            content=content,            # Original raw content
            cleaned_content=sanitized_content,
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

        # 7. Build Knowledge Graph (entity mentions + relationships)
        mentioned_entities = analysis.get("mentioned_entities", [])
        if mentioned_entities and isinstance(mentioned_entities, list):
            self._build_knowledge_graph(event.id, mentioned_entities, source_type, analysis.get("sentiment"))

        return analysis

    def _build_knowledge_graph(
        self,
        event_id,
        mentioned_entities: List[Dict],
        source_type: str,
        sentiment: Optional[float],
    ):
        """Creates EntityMention records and upserts EntityRelationship edges."""
        import logging
        from itertools import combinations
        from datetime import datetime, timezone

        logger = logging.getLogger(__name__)
        now = datetime.now(timezone.utc)

        # Normalize and deduplicate entities for this event
        seen_names = set()
        clean_entities = []
        for ent in mentioned_entities:
            name = ent.get("name", "").strip()
            ent_type = ent.get("type", "COMPANY").upper()
            if not name or name in seen_names:
                continue
            seen_names.add(name)
            clean_entities.append({"name": name, "type": ent_type})

        if not clean_entities:
            return

        # Build a lookup of tracked entities for resolution (name → entity_id)
        tracked_labels = {
            e.label.lower(): e.id
            for e in self.db.query(Entity).all()
        }

        # Create EntityMention records
        for ent in clean_entities:
            resolved_id = tracked_labels.get(ent["name"].lower())
            mention = EntityMention(
                event_id=event_id,
                mentioned_name=ent["name"],
                mentioned_type=ent["type"],
                resolved_entity_id=resolved_id,
            )
            self.db.add(mention)

        try:
            self.db.commit()
        except Exception as e:
            logger.warning(f"Failed to save entity mentions: {e}")
            self.db.rollback()
            return

        # Upsert EntityRelationship edges for every unique pair
        for ent_a, ent_b in combinations(clean_entities, 2):
            # Canonical ordering: always store (min_name, max_name) to prevent duplicate edges
            if ent_a["name"] > ent_b["name"]:
                ent_a, ent_b = ent_b, ent_a

            name_a, name_b = ent_a["name"], ent_b["name"]
            type_a, type_b = ent_a["type"], ent_b["type"]

            try:
                existing = self.db.query(EntityRelationship).filter(
                    EntityRelationship.entity_a_name == name_a,
                    EntityRelationship.entity_b_name == name_b,
                ).first()

                if existing:
                    existing.co_occurrence_count += 1
                    existing.last_seen = now
                    # Welford's online running average for sentiment
                    if sentiment is not None:
                        prev_avg = float(existing.avg_sentiment or 0)
                        n = existing.co_occurrence_count
                        existing.avg_sentiment = round(prev_avg + (sentiment - prev_avg) / n, 4)
                    # Merge source_type occurrence counts
                    src_counts = dict(existing.source_types or {})
                    src_counts[source_type] = src_counts.get(source_type, 0) + 1
                    existing.source_types = src_counts
                else:
                    rel = EntityRelationship(
                        entity_a_name=name_a,
                        entity_b_name=name_b,
                        entity_a_type=type_a,
                        entity_b_type=type_b,
                        co_occurrence_count=1,
                        avg_sentiment=round(sentiment, 4) if sentiment is not None else None,
                        first_seen=now,
                        last_seen=now,
                        source_types={source_type: 1},
                    )
                    self.db.add(rel)

                self.db.commit()
            except Exception as e:
                logger.warning(f"Failed to upsert relationship ({name_a}, {name_b}): {e}")
                self.db.rollback()

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
        
        if day_events:
            avg_sent = float(day_events[0]) if day_events[0] is not None else 0.0
            count = day_events[1] or 0
        else:
            avg_sent = 0.0
            count = 0
        
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
