import os
import feedparser
import urllib.parse
from typing import Dict, Any
from google.cloud import pubsub_v1
import json
import time
from intelligence_api.core.config import settings

class NewsScraper:
    def __init__(self, project_id: str, topic_id: str):
        self.publisher = pubsub_v1.PublisherClient()
        self.topic_path = self.publisher.topic_path(project_id, topic_id)

    def scrape_topic(self, topic: str, limit: int = 15, period: str = None):
        """Scrapes global news about a specific topic/entity using Google News RSS.
           'period' can be something like '7d', '30d', '1h', etc.
        """
        query = topic
        if period:
            query += f" when:{period}"
            
        encoded_query = urllib.parse.quote(query)
        rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"

        
        print(f"🕵️ Scaping Google News for: '{topic}'...")
        feed = feedparser.parse(rss_url)
        
        if not feed.entries:
            print(f"⚠️ No news found for '{topic}'.")
            return

        print(f"✅ Found {len(feed.entries)} news articles for '{topic}'. Processing top {limit}...")

        for entry in feed.entries[:limit]:
            # Google news provides title, link, published, and source
            source_name = getattr(entry, 'source', {}).get('title', 'Unknown News Source')
            
            payload = {
                "entity_label": topic,
                "content": f"{entry.title}\n{entry.get('description', '')}\nSource: {source_name}",
                "source_type": "News",
                "is_user": False,
                "raw_url": entry.link,
                "published_at": getattr(entry, 'published', None)
            }
            self.publish(payload)
            time.sleep(0.5) # Gentle pacing

    def publish(self, data: Dict[str, Any]):
        message_json = json.dumps(data)
        self.publisher.publish(self.topic_path, message_json.encode("utf-8"))
        print(f"✅ Published News article to Pub/Sub: {data['raw_url']}")

if __name__ == "__main__":
    # Local Test
    project = os.getenv("PROJECT_ID", "omnisight-35")
    topic = "raw-events"
    scraper = NewsScraper(project, topic)
    scraper.scrape_topic("Artificial Intelligence", limit=3)
