import os
import json
import logging
from google.cloud import pubsub_v1
from intelligence_api.core.config import settings
from intelligence_api.core.database import SessionLocal
from intelligence_api.application.processor import IntelligenceProcessor

logger = logging.getLogger(__name__)

def callback(message: pubsub_v1.subscriber.message.Message):
    """Callback triggered on every Pub/Sub message."""
    logger.info(f"📥 Received event: {message.data.decode('utf-8')}")
    try:
        payload = json.loads(message.data.decode("utf-8"))
        # Initialize DB session for this event
        db = SessionLocal()
        processor = IntelligenceProcessor(db)
        
        import asyncio
        # We need an event loop to run async process_event. 
        # Since this callback runs in a grpc background thread, we can run it synchronously.
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(processor.process_event(payload))
        loop.close()
        
        logger.info(f"✅ Successfully processed pubsub event. Sentiment: {result.get('sentiment')}")
        message.ack()
    except Exception as e:
        logger.error(f"❌ Failed to process pub/sub event: {e}")
        message.nack()
    finally:
        db.close()

def start_subscriber():
    """Starts the background subscriber listening to new intelligence events."""
    project_id = settings.PROJECT_ID
    subscription_id = "raw-events-sub"
    
    if not os.getenv("PUBSUB_EMULATOR_HOST"):
        os.environ["PUBSUB_EMULATOR_HOST"] = "localhost:8085"
    
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(project_id, subscription_id)
    
    logger.info(f"🎧 Listening for events on {subscription_path}...")
    
    # Non-blocking async subscribe
    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
    return streaming_pull_future
