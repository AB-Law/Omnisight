"""Unit tests for the correlation engine and market data service."""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import date, timedelta
from intelligence_api.application.correlation import CorrelationEngine, CorrelationResult
from intelligence_api.infrastructure.market_data import MarketDataService, TickerResolutionError


# ──── Ticker Resolution ────

class TestTickerResolution:
    def setup_method(self):
        self.service = MarketDataService()
        self.db = MagicMock()

    def test_cache_hit_returns_cached_ticker(self):
        """Should return cached ticker without calling APIs."""
        mock_mapping = MagicMock()
        mock_mapping.status = "resolved"
        mock_mapping.ticker_symbol = "AAPL"

        self.db.query().filter().first.return_value = mock_mapping

        result = self.service.resolve_ticker("Apple", self.db)
        assert result == "AAPL"

    @patch.object(MarketDataService, '_resolve_via_yfinance', return_value="MSFT")
    def test_yfinance_resolution_persists_to_db(self, mock_yf):
        """Should try yfinance and persist the mapping."""
        self.db.query().filter().first.return_value = None

        result = self.service.resolve_ticker("Microsoft", self.db)
        assert result == "MSFT"
        mock_yf.assert_called_once_with("Microsoft")
        self.db.commit.assert_called()

    @patch.object(MarketDataService, '_resolve_via_yfinance', return_value=None)
    @patch.object(MarketDataService, '_resolve_via_twelvedata', return_value=None)
    def test_both_fail_raises_error(self, mock_td, mock_yf):
        """Should raise TickerResolutionError and persist failure."""
        self.db.query().filter().first.return_value = None

        with pytest.raises(TickerResolutionError):
            self.service.resolve_ticker("NonExistentCo", self.db)

        self.db.commit.assert_called()  # failure persisted
    
    @patch.object(MarketDataService, '_resolve_via_yfinance', return_value=None)
    @patch.object(MarketDataService, '_resolve_via_twelvedata', return_value="GOOG")
    def test_twelvedata_fallback(self, mock_td, mock_yf):
        """Should fall back to Twelve Data when yfinance fails."""
        self.db.query().filter().first.return_value = None

        result = self.service.resolve_ticker("Google", self.db)
        assert result == "GOOG"
        mock_td.assert_called_once_with("Google")


# ──── Signal Strength ────

class TestSignalStrength:
    def setup_method(self):
        self.db = MagicMock()
        with patch('intelligence_api.application.correlation.MarketDataService'):
            self.engine = CorrelationEngine(self.db)

    def test_signal_strength_high_correlation_high_sample(self):
        """High |r| + many data points → high score."""
        score = self.engine._compute_signal_strength(0.85, 50)
        assert score >= 80

    def test_signal_strength_low_correlation(self):
        """Low |r| → low score regardless of sample size."""
        score = self.engine._compute_signal_strength(0.1, 50)
        assert score <= 15

    def test_signal_strength_penalizes_small_sample(self):
        """Same |r| but fewer data points → lower score."""
        high_sample = self.engine._compute_signal_strength(0.7, 40)
        low_sample = self.engine._compute_signal_strength(0.7, 5)
        assert high_sample > low_sample

    def test_signal_strength_clamped_at_100(self):
        """Should never exceed 100."""
        score = self.engine._compute_signal_strength(1.0, 100)
        assert score <= 100.0


# ──── Correlation Computation ────

class TestCorrelationComputation:
    def setup_method(self):
        self.db = MagicMock()
        with patch('intelligence_api.application.correlation.MarketDataService'):
            self.engine = CorrelationEngine(self.db)

    def test_insufficient_data_returns_zero_correlation(self):
        """Should handle < 3 common data points gracefully."""
        mock_entity = MagicMock()
        mock_entity.id = "test-id"
        self.db.query().filter().first.return_value = mock_entity

        self.engine.market.resolve_ticker.return_value = "TEST"
        
        # Only 1 price point
        mock_price = MagicMock()
        mock_price.date = date(2024, 1, 1)
        mock_price.close = 100.0
        self.engine.market.fetch_stock_prices.return_value = [mock_price]

        # Only 1 sentiment point on same date
        with patch.object(self.engine, 'get_sentiment_timeline', return_value=[
            {"date": date(2024, 1, 1), "avg_sentiment": 0.5, "event_count": 3}
        ]):
            result = self.engine.compute_correlation("TestCo", days=90)
            assert result.pearson_r == 0.0
            assert result.signal_strength == 0.0
            assert "Insufficient" in result.insight

    def test_insight_generation(self):
        """Should generate meaningful insight text."""
        insight = self.engine._generate_insight("Apple", "AAPL", 0.7, 2, 0.8, 75.0)
        assert "AAPL" in insight
        assert "2-day" in insight
        assert "Strong" in insight

    def test_no_signal_insight(self):
        """Should say no correlation when signal strength is very low."""
        insight = self.engine._generate_insight("Apple", "AAPL", 0.05, 0, 0.05, 5.0)
        assert "No meaningful" in insight
