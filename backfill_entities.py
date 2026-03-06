import os
import time
import json
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from intelligence_api.core.config import settings
from intelligence_api.domain.models import ScrapedEvent, EntityMention
from intelligence_api.application.processor import IntelligenceProcessor
from intelligence_api.infrastructure.ai_service import AIClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("BackfillScript")

def main():
    logger.info("Starting Knowledge Graph backfill script...")
    
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    processor = IntelligenceProcessor(db)
    ai_client = AIClient()

    try:
        # Find events that don't have any associated EntityMentions
        # By doing a LEFT JOIN and filtering where mention ID is NULL
        events_without_entities = db.query(ScrapedEvent).outerjoin(
            EntityMention, ScrapedEvent.id == EntityMention.event_id
        ).filter(EntityMention.id == None).all()
        
        total = len(events_without_entities)
        logger.info(f"Found {total} events to backfill with entities.")
        
        if total == 0:
            logger.info("Success! All events already have entities extracted.")
            return

        processed = 0
        for event in events_without_entities:
            try:
                # 1. Ask AI to extract entities from the content
                text_to_analyze = event.cleaned_content or event.content
                if not text_to_analyze:
                    continue
                
                logger.info(f"[{processed+1}/{total}] Analyzing event ID: {event.id}")
                
                # Make the LLM call
                analysis = ai_client.analyze_content(text_to_analyze)
                mentioned_entities = analysis.get("mentioned_entities", [])
                
                # 2. Build the knowledge graph (Mentions & Relationships) for this event
                if mentioned_entities:
                    processor._build_knowledge_graph(
                        event_id=event.id,
                        mentioned_entities=mentioned_entities,
                        source_type=event.source_type,
                        sentiment=float(event.sentiment_score) if event.sentiment_score else None
                    )
                    logger.info(f"  -> Extracted {len(mentioned_entities)} entities.")
                else:
                    # To prevent the script from re-analyzing this event on next run if it truly has no entities,
                    # We might want to add a dummy mention or flag, but for now we just rely on it occasionally retrying
                    # or being handled by a future boolean flag `entities_extracted`. 
                    # For simplicity of this PR, we just log and continue.
                    logger.info("  -> No entities found.")

                processed += 1
                
                # Simple rate limiting to avoid getting throttled by Azure OpenAI
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error processing event {event.id}: {e}")
                
    finally:
        db.close()
        logger.info("Backfill complete.")

if __name__ == "__main__":
    main()
