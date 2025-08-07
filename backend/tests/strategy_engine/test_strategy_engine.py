# tests/strategy_engine/test_strategy_engine.py
"""
Tests for the Strategy Engine core functionality
"""
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from decimal import Decimal

from core.db import get_async_session_context
from core.init import run_all
from models.db_models import Strategy, StrategyParameter
from core.strategy_engine import (
    StrategyEngine, validate_strategy, 
    calculate_strategy_performance, calculate_strategy_risk_metrics,
    validate_strategy_parameters
)


# Database Setup
@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Setup database once for all tests"""
    run_all()


@pytest.mark.asyncio
async def test_strategy_engine_initialization():
    """Test StrategyEngine initialization"""
    
    # Create test strategy
    strategy = Strategy(
        id=1,
        name="Test Momentum Strategy",
        description="Test strategy for momentum trading",
        strategy_type="momentum",
        risk_level="medium",
        workspace_id=1,
        created_by=1
    )
    
    # Create test parameters
    parameters = [
        StrategyParameter(
            id=1,
            strategy_id=1,
            parameter_name="lookback_period",
            parameter_type="int",
            default_value="20",
            current_value="20"
        ),
        StrategyParameter(
            id=2,
            strategy_id=1,
            parameter_name="momentum_threshold",
            parameter_type="float",
            default_value="0.05",
            current_value="0.05"
        )
    ]
    
    # Initialize engine
    engine = StrategyEngine(strategy, parameters)
    
    assert engine.strategy.name == "Test Momentum Strategy"
    assert engine.strategy.strategy_type == "momentum"
    assert len(engine.parameters) == 2
    assert "momentum" in engine.signal_generators


@pytest.mark.asyncio
async def test_momentum_signal_generation():
    """Test momentum signal generation"""
    
    strategy = Strategy(
        id=1,
        name="Momentum Test",
        strategy_type="momentum",
        risk_level="medium",
        workspace_id=1,
        created_by=1
    )
    
    parameters = [
        StrategyParameter(
            strategy_id=1,
            parameter_name="lookback_period",
            parameter_type="int",
            default_value="20",
            current_value="20"
        ),
        StrategyParameter(
            strategy_id=1,
            parameter_name="momentum_threshold",
            parameter_type="float",
            default_value="0.05",
            current_value="0.05"
        )
    ]
    
    engine = StrategyEngine(strategy, parameters)
    
    # Mock market data
    market_data = {
        "AAPL": {
            "prices": [150.0, 151.0, 152.0, 153.0, 154.0, 155.0, 156.0, 157.0, 158.0, 159.0,
                      160.0, 161.0, 162.0, 163.0, 164.0, 165.0, 166.0, 167.0, 168.0, 169.0, 170.0],
            "volumes": [100000] * 21
        }
    }
    
    signals = await engine.generate_signals(market_data)
    
    assert len(signals) > 0
    signal = signals[0]
    assert signal["symbol"] == "AAPL"
    assert signal["signal_type"] in ["buy", "sell", "hold"]
    assert "signal_strength" in signal
    assert "confidence_score" in signal


@pytest.mark.asyncio
async def test_mean_reversion_signal_generation():
    """Test mean reversion signal generation"""
    
    strategy = Strategy(
        id=2,
        name="Mean Reversion Test",
        strategy_type="mean_reversion",
        risk_level="medium",
        workspace_id=1,
        created_by=1
    )
    
    parameters = [
        StrategyParameter(
            strategy_id=2,
            parameter_name="bollinger_periods",
            parameter_type="int",
            default_value="20",
            current_value="20"
        ),
        StrategyParameter(
            strategy_id=2,
            parameter_name="bollinger_std",
            parameter_type="float",
            default_value="2.0",
            current_value="2.0"
        )
    ]
    
    engine = StrategyEngine(strategy, parameters)
    
    # Mock market data with mean reversion pattern
    market_data = {
        "MSFT": {
            "prices": [300.0, 305.0, 310.0, 315.0, 320.0, 318.0, 316.0, 314.0, 312.0, 310.0,
                      308.0, 306.0, 304.0, 302.0, 300.0, 298.0, 296.0, 294.0, 292.0, 290.0, 295.0],
            "volumes": [80000] * 21
        }
    }
    
    signals = await engine.generate_signals(market_data)
    
    assert len(signals) > 0
    signal = signals[0]
    assert signal["symbol"] == "MSFT"
    assert signal["signal_type"] in ["buy", "sell", "hold"]


@pytest.mark.asyncio
async def test_strategy_analysis():
    """Test strategy analysis functionality"""
    
    strategy = Strategy(
        id=3,
        name="Analysis Test Strategy",
        strategy_type="momentum",
        risk_level="high",
        workspace_id=1,
        created_by=1
    )
    
    parameters = [
        StrategyParameter(
            strategy_id=3,
            parameter_name="lookback_period",
            parameter_type="int",
            default_value="10",
            current_value="10"
        )
    ]
    
    engine = StrategyEngine(strategy, parameters)
    
    # Test analysis without backtest
    analysis = await engine.analyze_strategy(include_backtest=False)
    
    assert analysis.strategy_id == 3
    assert "risk_score" in analysis.risk_metrics
    assert isinstance(analysis.recommendations, list)
    assert analysis.analysis_timestamp is not None


@pytest.mark.asyncio
async def test_backtest_functionality():
    """Test strategy backtesting"""
    
    strategy = Strategy(
        id=4,
        name="Backtest Strategy",
        strategy_type="momentum",
        risk_level="medium",
        workspace_id=1,
        created_by=1
    )
    
    parameters = [
        StrategyParameter(
            strategy_id=4,
            parameter_name="lookback_period",
            parameter_type="int",
            default_value="20",
            current_value="20"
        )
    ]
    
    engine = StrategyEngine(strategy, parameters)
    
    start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end_date = datetime(2024, 12, 31, tzinfo=timezone.utc)
    initial_capital = Decimal("50000.00")
    
    backtest_result = await engine.backtest_strategy(
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital
    )
    
    assert backtest_result.strategy_id == 4
    assert backtest_result.start_date == start_date
    assert backtest_result.end_date == end_date
    assert isinstance(backtest_result.total_return, Decimal)
    assert isinstance(backtest_result.return_percentage, Decimal)


def test_calculate_strategy_performance():
    """Test strategy performance calculations"""
    
    # Mock trade data
    trades = [
        {"return": Decimal("100.00")},
        {"return": Decimal("-50.00")},
        {"return": Decimal("75.00")},
        {"return": Decimal("25.00")},
        {"return": Decimal("-25.00")}
    ]
    
    initial_capital = Decimal("10000.00")
    final_capital = Decimal("10125.00")
    
    performance = calculate_strategy_performance(trades, initial_capital, final_capital)
    
    assert performance["total_return"] == Decimal("125.00")
    assert performance["return_percentage"] == Decimal("1.25")
    assert performance["total_trades"] == 5
    assert performance["winning_trades"] == 3
    assert performance["losing_trades"] == 2
    assert performance["win_rate"] == Decimal("0.6000")


def test_calculate_strategy_risk_metrics():
    """Test strategy risk metrics calculation"""
    
    strategy = Strategy(
        id=5,
        name="Risk Test Strategy",
        strategy_type="momentum",
        risk_level="high",
        workspace_id=1,
        created_by=1
    )
    
    parameters = {
        "leverage": StrategyParameter(
            parameter_name="leverage",
            parameter_type="float",
            current_value="2.0"
        ),
        "stop_loss": StrategyParameter(
            parameter_name="stop_loss",
            parameter_type="float",
            current_value="5.0"
        )
    }
    
    risk_metrics = calculate_strategy_risk_metrics(strategy, parameters)
    
    assert "risk_score" in risk_metrics
    assert "risk_level" in risk_metrics
    assert risk_metrics["risk_score"] >= Decimal("0.00")
    assert risk_metrics["risk_score"] <= Decimal("1.00")
    assert risk_metrics["risk_level"] in ["low", "medium", "high"]


def test_validate_strategy_parameters():
    """Test parameter validation"""
    
    # Valid parameters
    valid_parameters = {
        "lookback_period": StrategyParameter(
            parameter_name="lookback_period",
            parameter_type="int",
            current_value="20",
            min_value="1",
            max_value="100",
            is_required=True
        ),
        "threshold": StrategyParameter(
            parameter_name="threshold",
            parameter_type="float",
            current_value="0.05",
            min_value="0.01",
            max_value="0.20",
            is_required=True
        )
    }
    
    validation = validate_strategy_parameters(valid_parameters)
    
    assert validation["is_valid"] is True
    assert len(validation["errors"]) == 0
    
    # Invalid parameters
    invalid_parameters = {
        "bad_int": StrategyParameter(
            parameter_name="bad_int",
            parameter_type="int",
            current_value="not_a_number",
            is_required=True
        ),
        "out_of_range": StrategyParameter(
            parameter_name="out_of_range",
            parameter_type="int",
            current_value="150",
            min_value="1",
            max_value="100",
            is_required=True
        )
    }
    
    validation = validate_strategy_parameters(invalid_parameters)
    
    assert validation["is_valid"] is False
    assert len(validation["errors"]) > 0


@pytest.mark.asyncio
async def test_validate_strategy():
    """Test complete strategy validation"""
    
    # Valid strategy
    valid_strategy = Strategy(
        id=6,
        name="Valid Strategy",
        strategy_type="momentum",
        risk_level="medium",
        workspace_id=1,
        created_by=1
    )
    
    valid_parameters = [
        StrategyParameter(
            parameter_name="lookback_period",
            parameter_type="int",
            current_value="20",
            is_required=True
        )
    ]
    
    validation = await validate_strategy(valid_strategy, valid_parameters)
    
    assert validation["is_valid"] is True
    assert len(validation["issues"]) == 0
    
    # Invalid strategy
    invalid_strategy = Strategy(
        id=7,
        name="",  # Empty name
        strategy_type="invalid_type",  # Invalid type
        workspace_id=1,
        created_by=1
    )
    
    validation = await validate_strategy(invalid_strategy, [])
    
    assert validation["is_valid"] is False
    assert len(validation["issues"]) > 0


@pytest.mark.asyncio
async def test_custom_strategy_engine():
    """Test custom strategy with code"""
    
    custom_strategy = Strategy(
        id=8,
        name="Custom Strategy",
        strategy_type="custom",
        strategy_code="# Simple momentum strategy\nif momentum > 0.05: signal = 'buy'",
        risk_level="medium",
        workspace_id=1,
        created_by=1
    )
    
    parameters = []
    
    engine = StrategyEngine(custom_strategy, parameters)
    
    assert "custom" in engine.signal_generators
    
    # Test signal generation (should handle safely)
    market_data = {
        "TEST": {
            "prices": [100.0, 101.0, 102.0],
            "volumes": [1000, 1100, 1200]
        }
    }
    
    signals = await engine.generate_signals(market_data)
    
    # Custom signal generator should return signals safely
    assert isinstance(signals, list)


@pytest.mark.asyncio
async def test_parameter_optimization():
    """Test parameter optimization functionality"""
    
    strategy = Strategy(
        id=9,
        name="Optimization Test",
        strategy_type="momentum",
        risk_level="medium",
        workspace_id=1,
        created_by=1
    )
    
    parameters = [
        StrategyParameter(
            parameter_name="lookback_period",
            parameter_type="int",
            current_value="20"
        )
    ]
    
    engine = StrategyEngine(strategy, parameters)
    
    optimization_result = await engine.optimize_parameters("sharpe_ratio")
    
    assert "optimization_target" in optimization_result
    assert "optimized_parameters" in optimization_result
    assert optimization_result["optimization_target"] == "sharpe_ratio"


def test_empty_trade_performance():
    """Test performance calculation with no trades"""
    
    performance = calculate_strategy_performance([], Decimal("10000.00"), Decimal("10000.00"))
    
    assert performance["total_return"] == Decimal("0.00")
    assert performance["return_percentage"] == Decimal("0.00")
    assert performance["total_trades"] == 0
    assert performance["win_rate"] is None
    assert performance["sharpe_ratio"] is None


@pytest.mark.asyncio
async def test_arbitrage_signal_generation():
    """Test arbitrage signal generation"""
    
    strategy = Strategy(
        id=10,
        name="Arbitrage Test",
        strategy_type="arbitrage",
        risk_level="low",
        workspace_id=1,
        created_by=1
    )
    
    parameters = [
        StrategyParameter(
            parameter_name="min_spread_percentage",
            parameter_type="float",
            current_value="0.5"
        )
    ]
    
    engine = StrategyEngine(strategy, parameters)
    
    # Mock market data with potential arbitrage opportunity
    market_data = {
        "AAPL": {
            "prices": [150.0],
            "volumes": [100000]
        },
        "AAPL2": {  # Similar asset with price difference
            "prices": [152.0],
            "volumes": [100000]
        }
    }
    
    signals = await engine.generate_signals(market_data)
    
    # Should generate signals for related assets
    assert isinstance(signals, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])