# core/backtesting_engine/__init__.py
"""
Backtesting Engine - Comprehensive historical strategy testing with real market data

This engine provides sophisticated backtesting capabilities separated from the Strategy Engine
for better modularity and specialized functionality.
"""
from .engine import BacktestEngine, BacktestResult, BacktestConfig
from .portfolio import SimulationPortfolio, SimulationPosition, SimulationTransaction
from .execution import ExecutionEngine, OrderType, OrderStatus
from .metrics import PerformanceMetrics, RiskMetrics

__all__ = [
    "BacktestEngine",
    "BacktestResult", 
    "BacktestConfig",
    "SimulationPortfolio",
    "SimulationPosition", 
    "SimulationTransaction",
    "ExecutionEngine",
    "OrderType",
    "OrderStatus",
    "PerformanceMetrics",
    "RiskMetrics"
]