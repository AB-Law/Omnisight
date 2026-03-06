import logging
from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from intelligence_api.core.database import SessionLocal
from intelligence_api.domain.models import ScrapeTarget
from intelligence_api.core.config import settings

logger = logging.getLogger(__name__)

def run_scraper(target: ScrapeTarget):
    """Dynamically runs the associated scraper for a target"""
    source = target.source_type
    name = target.target_name
    metadata = target.metadata_json or {}
    entity_type = metadata.get("entity_type", "COMPANY")
    discovery_depth = metadata.get("discovery_depth", 0)
    allow_discovery = metadata.get("allow_discovery", False)
    
    if source in ["Reddit Subreddit", "Reddit Hub"]:
        from data_ingestion.scrapers.reddit import RedditScraper
        scraper = RedditScraper(settings.PROJECT_ID, settings.PUBSUB_TOPIC)
        scraper.scrape_subreddit(name, limit=20, entity_type=entity_type, discovery_depth=discovery_depth, allow_discovery=allow_discovery)
    elif source in ["Google News", "Global News"]:
        from data_ingestion.scrapers.news import NewsScraper
        scraper = NewsScraper(settings.PROJECT_ID, settings.PUBSUB_TOPIC)
        
        # Get period from metadata if set
        period = metadata.get("period")
        # Increase limit if period is set to fetch 'more' data as requested
        max_results = 100 if period else 20
        scraper.scrape_topic(name, limit=max_results, period=period, entity_type=entity_type, discovery_depth=discovery_depth, allow_discovery=allow_discovery)
    elif source in ["Nitter/X User", "X (Twitter)"]:
        from data_ingestion.scrapers.nitter import NitterScraper
        scraper = NitterScraper(settings.PROJECT_ID, settings.PUBSUB_TOPIC)
        scraper.scrape_user(name, entity_type=entity_type, discovery_depth=discovery_depth, allow_discovery=allow_discovery)
    else:
        raise ValueError(f"Unknown source_type: {source}")


def process_pending_targets():
    """Finds pending targets that are due to be scraped next and runs them."""
    db: Session = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        
        # Find all targets that are Pending/Completed/Error and whose next_scrape_at has passed
        targets = db.query(ScrapeTarget).filter(
            ScrapeTarget.status.in_(["Pending", "Completed", "Error"]),
            ScrapeTarget.next_scrape_at <= now
        ).all()
        
        for target in targets:
            try:
                # 1. Mark as running
                target.status = "Running"
                db.commit()
                
                # 2. Run the actual web scraper (synchronously in this thread pool worker)
                run_scraper(target)
                
                # 3. Mark successful completion and schedule next run
                target.status = "Completed"
                target.error_message = None
                target.last_scraped_at = now
                
                # Calculate next_scrape_at
                interval = float(target.scrape_interval_minutes)
                if interval <= 0:
                    # If it's a 0-minute manual run, just set it to future so it doesn't infinite loop.
                    # Or 'Pending' state can handle it if we want manual only.
                    # We will set next run 1 year from now if interval=0 (i.e. strictly manual)
                    target.next_scrape_at = now + timedelta(days=365)
                else:
                    target.next_scrape_at = now + timedelta(minutes=interval)
                
                db.commit()
                logger.info(f"✅ Successfully scraped target {target.target_name}")
                
            except Exception as e:
                # 4. Handle failures gracefully
                logger.error(f"❌ Failed to scrape {target.target_name}: {e}")
                target.status = "Error"
                target.error_message = str(e)
                # Retry in 5 minutes regardless of interval
                target.next_scrape_at = now + timedelta(minutes=5)
                db.commit()
    
    except Exception as e:
        logger.error(f"Scheduler error processing targets: {e}")
    finally:
        db.close()


def refresh_market_data():
    """Daily job: refresh stock prices for all tracked tickers."""
    db: Session = SessionLocal()
    try:
        from intelligence_api.domain.models import TickerMapping
        from intelligence_api.infrastructure.market_data import MarketDataService
        
        service = MarketDataService()
        tickers = db.query(TickerMapping).filter(
            TickerMapping.status == "resolved",
            TickerMapping.ticker_symbol.isnot(None)
        ).all()
        
        for mapping in tickers:
            try:
                service.fetch_stock_prices(mapping.ticker_symbol, db, days=90)
                logger.info(f"📈 Refreshed market data for {mapping.ticker_symbol}")
            except Exception as e:
                logger.error(f"Failed to refresh {mapping.ticker_symbol}: {e}")
    except Exception as e:
        logger.error(f"Market data refresh error: {e}")
    finally:
        db.close()


def start_scheduler():
    scheduler = BackgroundScheduler()
    # Check for scrape jobs every 1 minute
    scheduler.add_job(
        process_pending_targets,
        trigger=IntervalTrigger(minutes=1),
        id="scrape_job",
        name="Periodic target scraper",
        replace_existing=True
    )
    # Refresh market data every 6 hours
    scheduler.add_job(
        refresh_market_data,
        trigger=IntervalTrigger(hours=6),
        id="market_data_refresh",
        name="Market data refresher",
        replace_existing=True
    )
    scheduler.start()
    logger.info("Background schedulers started (scraper + market data).")
    return scheduler
