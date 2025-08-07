# tests/backtesting_engine/test_service_simple.py
"""
Simple service layer tests for backtesting
"""
import pytest
from decimal import Decimal
from datetime import datetime, timezone


class TestBacktestingServiceHelpers:
    """Test helper functions in backtesting service"""
    
    def test_trade_to_dict(self):
        """Test converting BacktestTrade to dictionary"""
        from services.backtesting_service import _trade_to_dict
        from unittest.mock import Mock
        
        # Mock trade
        mock_trade = Mock()
        mock_trade.id = 1
        mock_trade.symbol = "AAPL"
        mock_trade.trade_type = "buy"
        mock_trade.quantity = 100
        mock_trade.price = Decimal("150.00")
        mock_trade.commission = Decimal("1.00")
        mock_trade.signal_timestamp = datetime(2024, 1, 1, tzinfo=timezone.utc)
        mock_trade.execution_timestamp = datetime(2024, 1, 1, tzinfo=timezone.utc)
        mock_trade.signal_strength = Decimal("0.8")
        mock_trade.confidence_score = Decimal("0.9")
        
        result = _trade_to_dict(mock_trade)
        
        assert result["id"] == 1
        assert result["symbol"] == "AAPL"
        assert result["trade_type"] == "buy"
        assert result["quantity"] == 100
        assert result["price"] == 150.0
        assert result["commission"] == 1.0
        assert result["signal_strength"] == 0.8
        assert result["confidence_score"] == 0.9
    
    def test_daily_metric_to_dict(self):
        """Test converting BacktestDailyMetric to dictionary"""
        from services.backtesting_service import _daily_metric_to_dict
        from unittest.mock import Mock
        
        # Mock daily metric
        mock_metric = Mock()
        mock_metric.date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        mock_metric.portfolio_value = Decimal("105000.00")
        mock_metric.daily_return = Decimal("0.02")
        mock_metric.cumulative_return = Decimal("0.05")
        mock_metric.drawdown = Decimal("0.01")
        mock_metric.trades_executed = 2
        mock_metric.positions_count = 3
        
        result = _daily_metric_to_dict(mock_metric)
        
        assert result["portfolio_value"] == 105000.0
        assert result["daily_return"] == 0.02
        assert result["cumulative_return"] == 0.05
        assert result["drawdown"] == 0.01
        assert result["trades_executed"] == 2
        assert result["positions_count"] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])