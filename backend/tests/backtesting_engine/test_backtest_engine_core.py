# tests/backtesting_engine/test_backtest_engine_core.py
"""
Tests for the core backtesting engine functionality
"""
import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, Mock

from core.backtesting_engine.engine import BacktestEngine, BacktestConfig
from core.backtesting_engine.portfolio import SimulationPortfolio


class TestBacktestConfig:
    """Test BacktestConfig dataclass"""
    
    def test_config_creation(self):
        """Test creating backtest configuration"""
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 2, 1, tzinfo=timezone.utc)
        
        config = BacktestConfig(
            start_date=start_date,
            end_date=end_date,
            initial_capital=Decimal("100000"),
            symbols=["AAPL", "MSFT"],
            commission_per_share=Decimal("0.01"),
            slippage=Decimal("0.001")
        )
        
        assert config.start_date == start_date
        assert config.end_date == end_date
        assert config.initial_capital == Decimal("100000")
        assert config.symbols == ["AAPL", "MSFT"]
        assert config.commission_per_share == Decimal("0.01")
        assert config.slippage == Decimal("0.001")


class TestBacktestEngine:
    """Test BacktestEngine core functionality"""
    
    def test_engine_initialization(self):
        """Test engine initialization with dependency injection"""
        strategy_config = {"id": 1, "type": "momentum", "name": "Test Strategy"}
        parameters = {"period": "20", "threshold": "0.02"}
        
        engine = BacktestEngine(strategy_config, parameters)
        
        assert engine.strategy_config == strategy_config
        assert engine.parameters == parameters
    
    def test_generate_trading_dates(self):
        """Test trading dates generation excludes weekends"""
        engine = BacktestEngine({}, {})
        
        # Test range that includes a weekend
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)  # Monday
        end_date = datetime(2024, 1, 8, tzinfo=timezone.utc)    # Monday
        
        trading_dates = engine._generate_trading_dates(start_date, end_date)
        
        # Should have 6 trading days (Mon-Fri, Mon)
        assert len(trading_dates) == 6
        
        # Check no weekends
        for date in trading_dates:
            assert date.weekday() < 5  # Monday=0, Friday=4
    
    def test_get_daily_market_data(self):
        """Test extracting daily market data from full dataset"""
        engine = BacktestEngine({}, {})
        
        # Mock market data
        market_data = {
            "AAPL": [
                {
                    "date": "2024-01-01T00:00:00",
                    "open": 150.0,
                    "high": 155.0,
                    "low": 148.0,
                    "close": 153.0,
                    "volume": 1000000
                },
                {
                    "date": "2024-01-02T00:00:00", 
                    "open": 153.0,
                    "high": 157.0,
                    "low": 152.0,
                    "close": 156.0,
                    "volume": 1200000
                }
            ]
        }
        
        target_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        daily_data = engine._get_daily_market_data(market_data, target_date)
        
        assert "AAPL" in daily_data
        assert daily_data["AAPL"]["open"] == Decimal("150.0")
        assert daily_data["AAPL"]["close"] == Decimal("153.0")
        assert daily_data["AAPL"]["volume"] == 1000000
        assert daily_data["AAPL"]["date"] == target_date
    
    def test_get_daily_market_data_missing(self):
        """Test handling missing market data for a date"""
        engine = BacktestEngine({}, {})
        
        market_data = {
            "AAPL": [
                {"date": "2024-01-01T00:00:00", "close": 153.0}
            ]
        }
        
        # Request data for date not in dataset
        target_date = datetime(2024, 1, 2, tzinfo=timezone.utc)
        daily_data = engine._get_daily_market_data(market_data, target_date)
        
        assert daily_data["AAPL"] is None
    
    @pytest.mark.asyncio
    async def test_risk_limits_check(self):
        """Test risk limit checking"""
        engine = BacktestEngine({}, {})
        portfolio = SimulationPortfolio(Decimal("100000"))
        
        config = BacktestConfig(
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=1),
            initial_capital=Decimal("100000"),
            symbols=["AAPL"],
            max_daily_loss=Decimal("0.05")  # 5% max daily loss
        )
        
        # Test normal conditions - should not stop
        daily_metric = {"daily_return": Decimal("-0.02")}  # 2% loss
        should_stop = await engine._check_risk_limits(portfolio, config, daily_metric)
        assert should_stop is False
        
        # Test excessive daily loss - should stop
        daily_metric = {"daily_return": Decimal("-0.08")}  # 8% loss
        should_stop = await engine._check_risk_limits(portfolio, config, daily_metric)
        assert should_stop is True
        
        # Test excessive drawdown - should stop
        daily_metric = {"drawdown": Decimal("0.30")}  # 30% drawdown
        should_stop = await engine._check_risk_limits(portfolio, config, daily_metric)
        assert should_stop is True
        
        # Test portfolio value too low - should stop
        portfolio.current_cash = Decimal("500")  # Below $1000 threshold
        daily_metric = {"daily_return": Decimal("0")}
        should_stop = await engine._check_risk_limits(portfolio, config, daily_metric)
        assert should_stop is True
    
    @pytest.mark.asyncio 
    async def test_full_backtest_integration(self):
        """Test full backtest execution with mocked dependencies"""
        strategy_config = {"id": 1, "type": "momentum", "name": "Test Strategy"}
        parameters = {"period": "20"}
        
        engine = BacktestEngine(strategy_config, parameters)
        
        # Create test configuration
        config = BacktestConfig(
            start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2024, 1, 3, tzinfo=timezone.utc),
            initial_capital=Decimal("100000"),
            symbols=["AAPL"]
        )
        
        # Mock market data
        market_data = {
            "AAPL": [
                {
                    "date": "2024-01-01T00:00:00",
                    "open": 150.0,
                    "high": 155.0, 
                    "low": 148.0,
                    "close": 153.0,
                    "volume": 1000000
                },
                {
                    "date": "2024-01-02T00:00:00",
                    "open": 153.0,
                    "high": 157.0,
                    "low": 152.0,
                    "close": 156.0,
                    "volume": 1200000
                }
            ]
        }
        
        # Mock strategy executor
        async def mock_strategy_executor(daily_data, date, params):
            signals = []
            for symbol, data in daily_data.items():
                if data and data["close"] > data["open"]:
                    signals.append({
                        "symbol": symbol,
                        "signal_type": "buy",
                        "quantity": 100,
                        "signal_strength": Decimal("0.8"),
                        "confidence_score": Decimal("0.7"),
                        "generated_at": date
                    })
            return signals
        
        # Mock progress callback
        progress_calls = []
        async def mock_progress_callback(progress, message):
            progress_calls.append((progress, message))
        
        # Execute backtest
        result = await engine.run_backtest(
            config=config,
            market_data=market_data,
            strategy_executor=mock_strategy_executor,
            progress_callback=mock_progress_callback
        )
        
        # Verify results
        assert result is not None
        assert result.strategy_id == 1
        assert result.config == config
        assert result.total_trades >= 0
        assert result.execution_duration > 0
        assert len(progress_calls) > 0  # Progress was reported
        
        # Check that progress was reported
        progress_values = [call[0] for call in progress_calls]
        assert 15 in progress_values  # Initial progress
        assert 100 in progress_values  # Completion


class TestBacktestEngineErrorHandling:
    """Test error handling in backtest engine"""
    
    @pytest.mark.asyncio
    async def test_backtest_failure_handling(self):
        """Test that backtest failures are handled gracefully"""
        engine = BacktestEngine({}, {})
        
        config = BacktestConfig(
            start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2024, 1, 2, tzinfo=timezone.utc),
            initial_capital=Decimal("100000"),
            symbols=["AAPL"]
        )
        
        # Mock strategy executor that raises exception
        async def failing_strategy_executor(daily_data, date, params):
            raise ValueError("Strategy execution failed")
        
        # Mock progress callback
        error_reported = False
        async def error_progress_callback(progress, message):
            nonlocal error_reported
            if progress == -1:
                error_reported = True
        
        # Execute backtest - should raise exception
        with pytest.raises(ValueError, match="Strategy execution failed"):
            await engine.run_backtest(
                config=config,
                market_data={"AAPL": []},
                strategy_executor=failing_strategy_executor,
                progress_callback=error_progress_callback
            )
        
        # Check error was reported via progress callback
        assert error_reported is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])