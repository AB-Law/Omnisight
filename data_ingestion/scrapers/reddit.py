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

    def scrape_subreddit(self, subreddit_name: str, limit: int = 10):
        """Scrapes a subreddit using official PRAW library."""
        print(f"🕵️ Scaping r/{subreddit_name} via PRAW...")
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            for submission in subreddit.new(limit=limit):
                payload = {
                    "entity_label": subreddit_name,
                    "content": f"{submission.title}\n{submission.selftext}",
                    "source_type": "Reddit",
                    "is_user": False,
                    "raw_url": f"https://reddit.com{submission.permalink}",
                    "published_at": submission.created_utc
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
