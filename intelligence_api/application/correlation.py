import logging
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
from datetime import date, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import cast, Date as SqlDate, func as sa_func

from intelligence_api.domain.models import Entity, ScrapedEvent, DailyTrend
from intelligence_api.infrastructure.market_data import MarketDataService, TickerResolutionError

logger = logging.getLogger(__name__)


@dataclass
class CorrelationResult:
    entity_label: str
    ticker_symbol: str
    pearson_r: float               # -1 to +1 (overall correlation)
    best_lag_days: int             # lag with strongest correlation
    best_lag_r: float              # correlation at best lag
    signal_strength: float         # 0..100 composite score
    data_points: int               # number of aligned data points
    aligned_data: List[Dict] = field(default_factory=list)
    lag_analysis: List[Dict] = field(default_factory=list)
    insight: str = ""

    def to_dict(self):
        return asdict(self)


class CorrelationEngine:
    def __init__(self, db: Session):
        self.db = db
        self.market = MarketDataService()

    def get_sentiment_timeline(self, entity_id, days: int = 90) -> List[Dict]:
        """
        Get daily aggregated sentiment for an entity.
        Uses events table directly, grouped by date.
        """
        cutoff = date.today() - timedelta(days=days)

        results = self.db.query(
            cast(ScrapedEvent.published_at, SqlDate).label("obs_date"),
            sa_func.avg(ScrapedEvent.sentiment_score).label("avg_sentiment"),
            sa_func.count(ScrapedEvent.id).label("event_count")
        ).filter(
            ScrapedEvent.entity_id == entity_id,
            ScrapedEvent.published_at is not None,
            cast(ScrapedEvent.published_at, SqlDate) >= cutoff
        ).group_by(
            cast(ScrapedEvent.published_at, SqlDate)
        ).order_by(
            cast(ScrapedEvent.published_at, SqlDate)
        ).all()

        return [
            {
                "date": row.obs_date,
                "avg_sentiment": float(row.avg_sentiment) if row.avg_sentiment else 0.0,
                "event_count": row.event_count
            }
            for row in results
        ]

    def compute_correlation(self, entity_label: str, days: int = 90) -> CorrelationResult:
        """
        Main entry point: align sentiment timeline with stock prices and compute
        Pearson correlation + lag analysis + Signal Strength.
        """
        # 1. Find entity
        entity = self.db.query(Entity).filter(
            Entity.label == entity_label,
            Entity.type == "COMPANY"
        ).first()
        if not entity:
            raise ValueError(f"No COMPANY entity found for '{entity_label}'")

        # 2. Resolve ticker
        ticker = self.market.resolve_ticker(entity_label, self.db)

        # 3. Fetch stock prices
        prices = self.market.fetch_stock_prices(ticker, self.db, days=days)
        if not prices:
            raise ValueError(f"No stock price data available for {ticker}")

        # 4. Get sentiment timeline
        sentiment_data = self.get_sentiment_timeline(entity.id, days=days)
        if not sentiment_data:
            raise ValueError(f"No sentiment data available for '{entity_label}'")

        # 5. Align by date (inner join)
        price_by_date = {p.date: float(p.close) for p in prices if p.close}
        sentiment_by_date = {s["date"]: s["avg_sentiment"] for s in sentiment_data}

        common_dates = sorted(set(price_by_date.keys()) & set(sentiment_by_date.keys()))
        
        if len(common_dates) < 3:
            # Not enough overlapping data
            return CorrelationResult(
                entity_label=entity_label,
                ticker_symbol=ticker,
                pearson_r=0.0,
                best_lag_days=0,
                best_lag_r=0.0,
                signal_strength=0.0,
                data_points=len(common_dates),
                aligned_data=[
                    {
                        "date": d.isoformat(),
                        "sentiment": sentiment_by_date.get(d),
                        "close_price": price_by_date.get(d)
                    }
                    for d in common_dates
                ],
                insight=f"Insufficient overlapping data ({len(common_dates)} days) for meaningful correlation."
            )

        sentiments = [sentiment_by_date[d] for d in common_dates]
        closes = [price_by_date[d] for d in common_dates]

        # 6. Compute Pearson correlation (lag 0)
        from scipy.stats import pearsonr
        pearson_r, p_value = pearsonr(sentiments, closes)

        # 7. Lag analysis (1-5 days)
        lag_results = [{"lag": 0, "correlation": round(pearson_r, 4), "p_value": round(p_value, 4)}]
        
        # Build full aligned series for lag computation
        all_dates_sorted = sorted(set(price_by_date.keys()) | set(sentiment_by_date.keys()))
        
        best_lag = 0
        best_lag_r = pearson_r

        for lag in range(1, 6):
            # For each price date, pair with sentiment from `lag` days earlier
            lagged_pairs = []
            for d in sorted(price_by_date.keys()):
                lagged_date = d - timedelta(days=lag)
                if lagged_date in sentiment_by_date:
                    lagged_pairs.append((sentiment_by_date[lagged_date], price_by_date[d]))

            if len(lagged_pairs) >= 3:
                s_vals, p_vals = zip(*lagged_pairs)
                lag_r, lag_p = pearsonr(list(s_vals), list(p_vals))
                lag_results.append({
                    "lag": lag,
                    "correlation": round(lag_r, 4),
                    "p_value": round(lag_p, 4),
                    "pairs": len(lagged_pairs)
                })
                if abs(lag_r) > abs(best_lag_r):
                    best_lag = lag
                    best_lag_r = lag_r
            else:
                lag_results.append({"lag": lag, "correlation": None, "pairs": len(lagged_pairs)})

        # 8. Signal Strength score
        signal_strength = self._compute_signal_strength(best_lag_r, len(common_dates))

        # 9. Generate insight text
        insight = self._generate_insight(entity_label, ticker, pearson_r, best_lag, best_lag_r, signal_strength)

        # 10. Aligned data for charting
        aligned_data = [
            {
                "date": d.isoformat(),
                "sentiment": round(sentiment_by_date[d], 4),
                "close_price": round(price_by_date[d], 2)
            }
            for d in common_dates
        ]

        return CorrelationResult(
            entity_label=entity_label,
            ticker_symbol=ticker,
            pearson_r=round(pearson_r, 4),
            best_lag_days=best_lag,
            best_lag_r=round(best_lag_r, 4),
            signal_strength=round(signal_strength, 1),
            data_points=len(common_dates),
            aligned_data=aligned_data,
            lag_analysis=lag_results,
            insight=insight
        )

    def _compute_signal_strength(self, best_lag_r: float, sample_size: int) -> float:
        """
        Signal Strength: 0-100 composite score.
        Based on the strongest lag correlation, penalized by small sample size.
        """
        # Confidence factor: scale from 0.3 (very few points) to 1.0 (enough points)
        if sample_size >= 30:
            confidence = 1.0
        elif sample_size >= 15:
            confidence = 0.7 + (sample_size - 15) * (0.3 / 15)
        else:
            confidence = max(0.3, sample_size / 15 * 0.7)

        raw_score = abs(best_lag_r) * 100
        return min(100.0, raw_score * confidence)

    def _generate_insight(self, entity: str, ticker: str, pearson_r: float,
                          best_lag: int, best_lag_r: float, signal_strength: float) -> str:
        """Generate a human-readable insight sentence."""
        direction = "positive" if best_lag_r > 0 else "negative"
        strength_word = "strong" if signal_strength >= 60 else "moderate" if signal_strength >= 30 else "weak"

        if best_lag == 0:
            timing = "same-day"
        else:
            timing = f"{best_lag}-day leading"

        if signal_strength < 10:
            return f"No meaningful correlation found between OSINT sentiment and {ticker} price movement."

        return (
            f"{strength_word.capitalize()} {direction} {timing} correlation detected: "
            f"OSINT sentiment {'preceded' if best_lag > 0 else 'correlated with'} "
            f"{ticker} price movements with {signal_strength:.0f}% signal strength."
        )


def get_sector_heatmap_data(db: Session) -> List[Dict]:
    """
    Aggregate sentiment and entity count by sector for heatmap visualization.
    """
    results = db.query(
        Entity.sector,
        sa_func.count(Entity.id).label("entity_count"),
        sa_func.avg(ScrapedEvent.sentiment_score).label("avg_sentiment"),
        sa_func.count(ScrapedEvent.id).label("total_events")
    ).join(
        ScrapedEvent, ScrapedEvent.entity_id == Entity.id
    ).filter(
        Entity.sector.isnot(None),
        Entity.sector != "Unknown"
    ).group_by(
        Entity.sector
    ).all()

    return [
        {
            "sector": row.sector,
            "entity_count": row.entity_count,
            "avg_sentiment": round(float(row.avg_sentiment), 4) if row.avg_sentiment else 0.0,
            "total_events": row.total_events
        }
        for row in results
    ]
