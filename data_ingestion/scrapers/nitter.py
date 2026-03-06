import os
import feedparser
from typing import Dict, Any
from google.cloud import pubsub_v1
import json
import time
from intelligence_api.core.config import settings

class NitterScraper:
    def __init__(self, project_id: str, topic_id: str):
        self.publisher = pubsub_v1.PublisherClient()
        self.topic_path = self.publisher.topic_path(project_id, topic_id)
        self.instance = settings.NITTER_INSTANCE.rstrip('/')

    def scrape_user(self, username: str):
        """Scrapes a Twitter user via Nitter's RSS feed."""
        # Nitter RSS format: https://nitter.net/username/rss
        rss_url = f"{self.instance}/{username}/rss"
        
        print(f"🕵️ Scaping X/Twitter (via Nitter) for @{username}...")
        feed = feedparser.parse(rss_url)
        
        if not feed.entries:
            print(f"⚠️ No entries found for @{username} on instance {self.instance}. Nitter instances are often rate-limited.")
            return

        print(f"✅ Found {len(feed.entries)} entries for @{username}")

        for entry in feed.entries:
            payload = {
                "entity_label": username,
                "content": entry.get("description", entry.title),
                "source_type": "Nitter",
                "is_user": True, # Twitter handles are usually individuals/accounts
                "raw_url": entry.link,
                "published_at": getattr(entry, 'published', None)
            }
            self.publish(payload)
            time.sleep(1) # Be a good citizen

    def publish(self, data: Dict[str, Any]):
        message_json = json.dumps(data)
        self.publisher.publish(self.topic_path, message_json.encode("utf-8"))
        print(f"✅ Published Nitter tweet to Pub/Sub: {data['raw_url']}")

if __name__ == "__main__":
    # Local Test
    project = os.getenv("PROJECT_ID", "omnisight-35")
    topic = "raw-events"
    scraper = NitterScraper(project, topic)
    scraper.scrape_user("elonkmusk_news") # Example
