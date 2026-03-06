import logging
from typing import Optional, List
from datetime import datetime, timedelta, date
from decimal import Decimal

from sqlalchemy.orm import Session
from intelligence_api.domain.models import TickerMapping, StockPrice
from intelligence_api.core.config import settings

logger = logging.getLogger(__name__)


class TickerResolutionError(Exception):
    """Raised when a company name cannot be resolved to a ticker symbol."""
    pass


class MarketDataService:
    """Handles ticker resolution (with DB caching) and stock price fetching."""

    def resolve_ticker(self, company_name: str, db: Session) -> str:
        """
        Resolve a company name to a ticker symbol.
        Checks DB cache first, then tries yfinance, then Twelve Data.
        Persists both successes and failures in ticker_mappings.
        """
        # 1. Check DB cache
        cached = db.query(TickerMapping).filter(
            TickerMapping.company_name == company_name.lower()
        ).first()

        if cached:
            if cached.status == "resolved" and cached.ticker_symbol:
                logger.info(f"Ticker cache hit: {company_name} → {cached.ticker_symbol}")
                return cached.ticker_symbol
            elif cached.status == "failed":
                # Check if the failure is recent (< 24h) to avoid re-trying
                if cached.updated_at and (datetime.utcnow() - cached.updated_at).total_seconds() < 86400:
                    raise TickerResolutionError(
                        f"Recently failed to resolve '{company_name}': {cached.error_message}"
                    )
                # Stale failure — retry below

        # 2. Try yfinance
        ticker_symbol = self._resolve_via_yfinance(company_name)
        if ticker_symbol:
            self._persist_mapping(db, company_name, ticker_symbol, resolved_via="yfinance")
            return ticker_symbol

        # 3. Try Twelve Data
        ticker_symbol = self._resolve_via_twelvedata(company_name)
        if ticker_symbol:
            self._persist_mapping(db, company_name, ticker_symbol, resolved_via="twelvedata")
            return ticker_symbol

        # 4. Both failed — persist failure
        self._persist_failure(db, company_name, "Could not resolve ticker via yfinance or Twelve Data")
        raise TickerResolutionError(f"Could not resolve ticker for '{company_name}'")

    def _resolve_via_yfinance(self, company_name: str) -> Optional[str]:
        """Try to resolve company name using yfinance search."""
        try:
            import yfinance as yf
            
            # 1. Try search first (most reliable for company names)
            search = yf.Search(company_name)
            if search.quotes:
                # Prioritize 'equity' type and 'US' market if available
                equities = [q for q in search.quotes if q.get("quoteType") == "EQUITY"]
                target_quotes = equities if equities else search.quotes
                
                # Further refine by common US exchanges if possible
                for q in target_quotes:
                    if any(exch in q.get("exchange", "") for exch in ["NMS", "NYQ", "NAS", "NYS"]):
                        return q.get("symbol")
                
                return target_quotes[0].get("symbol")

            # 2. Only try direct ticker lookup if it looks like a ticker (1-5 chars, uppercase)
            if 1 <= len(company_name) <= 5 and company_name.isupper():
                ticker = yf.Ticker(company_name)
                # Note: .info is very slow; avoid if possible
                if ticker.history(period="1d").empty is False:
                    return company_name

        except Exception as e:
            logger.warning(f"yfinance resolution failed for '{company_name}': {e}")
        return None

    def _resolve_via_twelvedata(self, company_name: str) -> Optional[str]:
        """Fallback: use Twelve Data symbol search API."""
        api_key = settings.TWELVE_DATA_API_KEY
        if not api_key:
            logger.warning("TWELVE_DATA_API_KEY not configured, skipping Twelve Data fallback")
            return None

        try:
            from twelvedata import TDClient
            td = TDClient(apikey=api_key)
            results = td.symbol_search(symbol=company_name).as_json()
            if results and len(results) > 0:
                # Prefer US exchanges
                for r in results:
                    if r.get("country", "").lower() == "united states":
                        return r["symbol"]
                return results[0]["symbol"]
        except Exception as e:
            logger.warning(f"Twelve Data resolution failed for '{company_name}': {e}")
        return None

    def _persist_mapping(self, db: Session, company_name: str, ticker: str,
                         resolved_via: str, exchange: str = None):
        """Upsert a successful ticker mapping."""
        existing = db.query(TickerMapping).filter(
            TickerMapping.company_name == company_name.lower()
        ).first()

        if existing:
            existing.ticker_symbol = ticker
            existing.resolved_via = resolved_via
            existing.exchange = exchange
            existing.status = "resolved"
            existing.error_message = None
        else:
            mapping = TickerMapping(
                company_name=company_name.lower(),
                ticker_symbol=ticker,
                exchange=exchange,
                resolved_via=resolved_via,
                status="resolved"
            )
            db.add(mapping)
        db.commit()

    def _persist_failure(self, db: Session, company_name: str, error: str):
        """Upsert a failed ticker mapping for tracking."""
        existing = db.query(TickerMapping).filter(
            TickerMapping.company_name == company_name.lower()
        ).first()

        if existing:
            existing.status = "failed"
            existing.error_message = error
        else:
            mapping = TickerMapping(
                company_name=company_name.lower(),
                status="failed",
                error_message=error
            )
            db.add(mapping)
        db.commit()

    def fetch_stock_prices(self, ticker: str, db: Session, days: int = 90) -> List[StockPrice]:
        """
        Fetch daily stock prices for a ticker.
        Checks DB for existing rows and only fetches missing date ranges.
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        # Check existing data range in DB
        existing_dates = set()
        existing = db.query(StockPrice.date).filter(
            StockPrice.ticker_symbol == ticker,
            StockPrice.date >= start_date,
            StockPrice.date <= end_date
        ).all()
        existing_dates = {row.date for row in existing}

        # If we have recent data (within 1 day), return cached
        if existing_dates and max(existing_dates) >= end_date - timedelta(days=1):
            logger.info(f"Stock data for {ticker} is up to date in DB")
            return db.query(StockPrice).filter(
                StockPrice.ticker_symbol == ticker,
                StockPrice.date >= start_date
            ).order_by(StockPrice.date).all()

        # Fetch from APIs
        new_prices = self._fetch_via_yfinance(ticker, start_date, end_date)
        if not new_prices:
            new_prices = self._fetch_via_twelvedata(ticker, start_date, end_date)

        # Upsert new prices
        for price_data in new_prices:
            if price_data["date"] not in existing_dates:
                price = StockPrice(
                    ticker_symbol=ticker,
                    date=price_data["date"],
                    open=price_data.get("open"),
                    high=price_data.get("high"),
                    low=price_data.get("low"),
                    close=price_data.get("close"),
                    volume=price_data.get("volume")
                )
                db.add(price)
        db.commit()

        return db.query(StockPrice).filter(
            StockPrice.ticker_symbol == ticker,
            StockPrice.date >= start_date
        ).order_by(StockPrice.date).all()

    def _fetch_via_yfinance(self, ticker: str, start_date: date, end_date: date) -> list:
        """Fetch daily prices from yfinance."""
        try:
            import yfinance as yf
            data = yf.download(
                ticker,
                start=start_date.isoformat(),
                end=end_date.isoformat(),
                progress=False
            )
            if data.empty:
                return []

            prices = []
            for idx, row in data.iterrows():
                dt = idx.date() if hasattr(idx, 'date') else idx
                prices.append({
                    "date": dt,
                    "open": float(row.get(("Open", ticker), row.get("Open", 0))),
                    "high": float(row.get(("High", ticker), row.get("High", 0))),
                    "low": float(row.get(("Low", ticker), row.get("Low", 0))),
                    "close": float(row.get(("Close", ticker), row.get("Close", 0))),
                    "volume": int(row.get(("Volume", ticker), row.get("Volume", 0))),
                })
            logger.info(f"Fetched {len(prices)} days of price data for {ticker} via yfinance")
            return prices
        except Exception as e:
            logger.warning(f"yfinance price fetch failed for {ticker}: {e}")
            return []

    def _fetch_via_twelvedata(self, ticker: str, start_date: date, end_date: date) -> list:
        """Fallback: fetch from Twelve Data."""
        api_key = settings.TWELVE_DATA_API_KEY
        if not api_key:
            return []

        try:
            from twelvedata import TDClient
            td = TDClient(apikey=api_key)
            ts = td.time_series(
                symbol=ticker,
                interval="1day",
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                outputsize=5000
            ).as_json()

            prices = []
            for point in ts:
                prices.append({
                    "date": datetime.strptime(point["datetime"], "%Y-%m-%d").date(),
                    "open": float(point.get("open", 0)),
                    "high": float(point.get("high", 0)),
                    "low": float(point.get("low", 0)),
                    "close": float(point.get("close", 0)),
                    "volume": int(float(point.get("volume", 0))),
                })
            logger.info(f"Fetched {len(prices)} days of price data for {ticker} via Twelve Data")
            return prices
        except Exception as e:
            logger.warning(f"Twelve Data price fetch failed for {ticker}: {e}")
            return []
