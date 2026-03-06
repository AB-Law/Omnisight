import os
from google.cloud import pubsub_v1
from dotenv import load_dotenv

def reset_pubsub():
    load_dotenv()
    project_id = os.getenv("PROJECT_ID", "omnisight-project")
    topic_id = "raw-events"
    subscription_id = "raw-events-sub"
    
    # Check if running against emulator or default to local emulator
    if not os.getenv("PUBSUB_EMULATOR_HOST"):
        os.environ["PUBSUB_EMULATOR_HOST"] = "localhost:8085"
    
    print(f"Connecting to Pub/Sub Emulator at {os.getenv('PUBSUB_EMULATOR_HOST')}...")
    
    publisher = pubsub_v1.PublisherClient()
    subscriber = pubsub_v1.SubscriberClient()
    
    topic_path = publisher.topic_path(project_id, topic_id)
    subscription_path = subscriber.subscription_path(project_id, subscription_id)
    
    # Delete subscription first if it exists
    try:
        subscriber.delete_subscription(request={"subscription": subscription_path})
        print(f"Deleted subscription: {subscription_path}")
    except Exception as e:
        print(f"Subscription {subscription_id} not found or error deleting: {e}")
        
    # Delete topic if it exists
    try:
        publisher.delete_topic(request={"topic": topic_path})
        print(f"Deleted topic: {topic_path}")
    except Exception as e:
        print(f"Topic {topic_id} not found or error deleting: {e}")

    # Re-initialize using existing script
    print("Re-initializing Pub/Sub resources...")
    from scripts.init_pubsub import create_pubsub_resources
    create_pubsub_resources()
    print("✅ Pub/Sub reset complete.")

if __name__ == "__main__":
    reset_pubsub()
