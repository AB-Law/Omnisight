import os
import praw
from typing import List, Dict, Any
from google.cloud import pubsub_v1
import json
import time
from intelligence_api.core.config import settings

class RedditScraper:
    def __init__(self, project_id: str, topic_id: str):
        # Set up Pub/Sub
        self.publisher = pubsub_v1.PublisherClient()
        self.topic_path = self.publisher.topic_path(project_id, topic_id)
        
        # Set up PRAW
        self.reddit = praw.Reddit(
            client_id=settings.REDDIT_CLIENT_ID,
            client_secret=settings.REDDIT_CLIENT_SECRET,
            user_agent=os.getenv("REDDIT_USER_AGENT", "Omnisight/1.0"),
        )
        print(f"✅ Reddit Scraper initialized (Read-only: {self.reddit.read_only})")

    def scrape_subreddit(self, subreddit_name: str, limit: int = 25, entity_type: str = "COMPANY", discovery_depth: int = 0, allow_discovery: bool = False):
        """Fetches top posts from a subreddit and publishes to Pub/Sub."""
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            
            print(f"🕵️ Scraping /r/{subreddit_name}...")
            
            for post in subreddit.top(time_filter="day", limit=limit):
                payload = {
                    "entity_label": subreddit_name,
                    "entity_type": entity_type,
                    "content": f"{post.title}\n{post.selftext}",
                    "source_type": "Reddit",
                    "is_user": False,
                    "raw_url": f"https://reddit.com{post.permalink}",
                    "published_at": post.created_utc,
                    "discovery_depth": discovery_depth,
                    "allow_discovery": allow_discovery
                }
                self.publish(payload)
        except Exception as e:
            print(f"❌ Failed to scrape Reddit: {e}")

    def publish(self, data: Dict[str, Any]):
        message_json = json.dumps(data)
        self.publisher.publish(self.topic_path, message_json.encode("utf-8"))
        print(f"✅ Published Reddit post to Pub/Sub: {data['raw_url']}")

if __name__ == "__main__":
    # Local Test
    project = os.getenv("PROJECT_ID", "omnisight-35")
    topic = "raw-events"
    scraper = RedditScraper(project, topic)
    scraper.scrape_subreddit("technology", limit=5)
