import os
from dotenv import load_dotenv
load_dotenv()
from google.cloud import pubsub_v1

def create_pubsub_resources():
    project_id = os.getenv("PROJECT_ID", "omnisight-project")
    topic_id = "raw-events"
    
    # Check if running against emulator or default to local emulator
    if not os.getenv("PUBSUB_EMULATOR_HOST"):
        os.environ["PUBSUB_EMULATOR_HOST"] = "localhost:8085"
        
    print(f"Connecting to Pub/Sub Emulator at {os.getenv('PUBSUB_EMULATOR_HOST')}...")
    
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic_id)
    
    try:
        publisher.create_topic(request={"name": topic_path})
        print(f"Created topic: {topic_path}")
    except Exception as e:
        if "AlreadyExists" in str(e):
            print(f"Topic {topic_id} already exists.")
        else:
            print(f"Error creating topic: {e}")
            
    subscriber = pubsub_v1.SubscriberClient()
    subscription_id = "raw-events-sub"
    subscription_path = subscriber.subscription_path(project_id, subscription_id)
    
    try:
        subscriber.create_subscription(
            request={"name": subscription_path, "topic": topic_path}
        )
        print(f"Created subscription: {subscription_path}")
    except Exception as e:
        if "AlreadyExists" in str(e):
            print(f"Subscription {subscription_id} already exists.")
        else:
            print(f"Error creating subscription: {e}")

if __name__ == "__main__":
    create_pubsub_resources()
