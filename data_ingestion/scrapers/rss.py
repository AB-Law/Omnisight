import feedparser
import requests
import json
import os
from typing import List, Dict

class RSSScraper:
    def __init__(self, pubsub_client=None):
        self.pubsub = pubsub_client
        self.topic_path = os.getenv("PUBSUB_TOPIC_PATH", "projects/omnisight/topics/raw-events")

    def scrape_feeds(self, feeds: List[Dict[str, str]]):
        """
        feeds: List of dicts like {'url': '...', 'entity': '...', 'is_user': False}
        """
        for feed_info in feeds:
            feed = feedparser.parse(feed_info['url'])
            for entry in feed.entries:
                payload = {
                    "content": entry.title + " " + entry.description if 'description' in entry else entry.title,
                    "entity_label": feed_info['entity'],
                    "source_type": "RSS",
                    "raw_url": entry.link,
                    "is_user": feed_info['is_user']
                }
                self._publish(payload)

    def _publish(self, data: Dict):
        if self.pubsub:
            message_bytes = json.dumps(data).encode("utf-8")
            self.pubsub.publish(self.topic_path, message_bytes)
        else:
            print(f"[LOCAL SCRAPE] {data['entity_label']}: {data['content'][:50]}...")

if __name__ == "__main__":
    scraper = RSSScraper()
    mock_feeds = [
        {"url": "https://hnrss.org/frontpage", "entity": "Tech News", "is_user": False}
    ]
    scraper.scrape_feeds(mock_feeds)
