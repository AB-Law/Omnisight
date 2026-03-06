from google.cloud import pubsub_v1
import os
from sqlalchemy import create_engine, delete, text
from sqlalchemy.orm import sessionmaker
from intelligence_api.core.config import settings
from intelligence_api.domain.models import Entity, ScrapeTarget, ScrapedEvent

# --- 1. Clear Pub/Sub ---
project_id = settings.PROJECT_ID
subscription_id = "raw-events-sub"

if not os.getenv("PUBSUB_EMULATOR_HOST"):
    os.environ["PUBSUB_EMULATOR_HOST"] = "localhost:8085"

subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(project_id, subscription_id)

print(f"🧹 Purging Pub/Sub subscription: {subscription_id}")
try:
    # We pull with max_messages and return_immediately to flush it
    response = subscriber.pull(
        request={"subscription": subscription_path, "max_messages": 1000, "return_immediately": True}
    )
    ack_ids = [msg.ack_id for msg in response.received_messages]
    if ack_ids:
        subscriber.acknowledge(request={"subscription": subscription_path, "ack_ids": ack_ids})
        print(f"✅ Acknowledged {len(ack_ids)} stale messages.")
    else:
        print("✅ No messages to clear.")
except Exception as e:
    print(f"⚠️ Pub/Sub clear failed (maybe empty?): {e}")


# --- 2. Clean DB ---
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

print("🧹 Cleaning Database...")

# Blacklist of generic terms misidentified as people
PERSONA_BLACKLIST = [
    "CEO", "CFO", "CTO", "COO", "C.E.O.", "C.E.O", "Founder", "Founders", "Co-Founder", 
    "Chairman", "President", "Director", "Executive", "Executives",
    "Spokesperson", "Representative", "Americans", "People", "Employees", 
    "Analysts", "Investors", "Users", "Customers", "Staff", "Team", 
    "Board", "Members", "Others", "Someone", "Anyone", "The Company"
]

# 1. Find the IDs of entities to be removed
for name in PERSONA_BLACKLIST:
    entities_to_remove = db.query(Entity).filter(Entity.type == "PERSON", Entity.label.ilike(f"%{name}%")).all()
    entity_ids = [e.id for e in entities_to_remove]
    
    if not entity_ids:
        continue

    # A. Delete Targets for blacklisted names/entities
    db.query(ScrapeTarget).filter(ScrapeTarget.target_name.ilike(f"%{name}%")).delete(synchronize_session=False)

    # B. Delete related events
    db.query(ScrapedEvent).filter(ScrapedEvent.entity_id.in_(entity_ids)).delete(synchronize_session=False)

    # C. Delete daily trends
    from intelligence_api.domain.models import DailyTrend
    db.query(DailyTrend).filter(DailyTrend.entity_id.in_(entity_ids)).delete(synchronize_session=False)

    # D. Delete mentions
    from intelligence_api.domain.models import EntityMention
    db.query(EntityMention).filter(EntityMention.mentioned_name.ilike(f"%{name}%")).delete(synchronize_session=False)
    db.query(EntityMention).filter(EntityMention.resolved_entity_id.in_(entity_ids)).delete(synchronize_session=False)

    # E. Delete relationships (using names)
    from intelligence_api.domain.models import EntityRelationship
    db.query(EntityRelationship).filter(
        (EntityRelationship.entity_a_name.ilike(f"%{name}%")) | 
        (EntityRelationship.entity_b_name.ilike(f"%{name}%"))
    ).delete(synchronize_session=False)

    # F. Finally, delete the Entities
    db.query(Entity).filter(Entity.id.in_(entity_ids)).delete(synchronize_session=False)

db.commit()
print("✅ Database deep cleaned.")
db.close()
