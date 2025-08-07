# core/strategy_engine/__init__.py
"""
Strategy Engine - Trading strategy analysis and signal generation

This module provides:
- StrategyEngine: Core engine for strategy analysis and signal generation (backtesting moved to separate engine)
- Signal generators for different strategy types (momentum, mean reversion, arbitrage, custom)
- Risk calculation and parameter validation utilities
- DataService integration for real market data

Note: Backtesting functionality has been moved to a separate Backtesting Engine for better modularity
"""

from .engine import StrategyEngine, StrategyAnalysisResult, validate_strategy
from .calculations import (
    calculate_strategy_risk_metrics,
    validate_strategy_parameters,
    evaluate_strategy_signals,
    calculate_correlation_matrix
)
from .signal_generators import (
    BaseSignalGenerator,
    MomentumSignalGenerator,
    MeanReversionSignalGenerator,
    ArbitrageSignalGenerator,
    CustomSignalGenerator
)

__all__ = [
    # Core engine
    "StrategyEngine",
    "StrategyAnalysisResult", 
    "validate_strategy",
    
    # Calculations
    "calculate_strategy_risk_metrics", 
    "validate_strategy_parameters",
    "evaluate_strategy_signals",
    "calculate_correlation_matrix",
    
    # Signal generators
    "BaseSignalGenerator",
    "MomentumSignalGenerator",
    "MeanReversionSignalGenerator", 
    "ArbitrageSignalGenerator",
    "CustomSignalGenerator"
]