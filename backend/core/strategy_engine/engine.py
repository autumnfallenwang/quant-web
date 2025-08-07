# core/strategy_engine/engine.py
"""
Strategy Engine - Core implementation for trading strategy analysis and signal generation
Refactored to remove backtesting (moved to separate Backtesting Engine) and integrate DataService
"""
from datetime import datetime, timezone, date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from models.db_models import Strategy, StrategyParameter
from services.data_service import DataService
from .calculations import (
    calculate_strategy_risk_metrics,
    validate_strategy_parameters
)
from .signal_generators import MomentumSignalGenerator, MeanReversionSignalGenerator, ArbitrageSignalGenerator


@dataclass
class StrategyAnalysisResult:
    """Result of strategy analysis"""
    strategy_id: int
    performance_metrics: Dict[str, Any]
    risk_metrics: Dict[str, Any]
    signal_analysis: Dict[str, Any]
    recommendations: List[str]
    analysis_timestamp: datetime




class StrategyEngine:
    """Core strategy engine for analysis and signal generation (backtesting moved to separate engine)"""
    
    def __init__(self, strategy: Strategy, parameters: List[StrategyParameter]):
        self.strategy = strategy
        self.parameters = {param.parameter_name: param for param in parameters}
        self.data_service = DataService()
        self.signal_generators = self._initialize_signal_generators()
    
    def _initialize_signal_generators(self) -> Dict[str, Any]:
        """Initialize signal generators based on strategy type"""
        generators = {}
        
        if self.strategy.strategy_type == "momentum":
            generators["momentum"] = MomentumSignalGenerator(self.parameters)
        elif self.strategy.strategy_type == "mean_reversion":
            generators["mean_reversion"] = MeanReversionSignalGenerator(self.parameters)
        elif self.strategy.strategy_type == "arbitrage":
            generators["arbitrage"] = ArbitrageSignalGenerator(self.parameters)
        elif self.strategy.strategy_type == "custom":
            # For custom strategies, we'll implement a dynamic code execution system
            generators["custom"] = self._create_custom_generator()
        
        return generators
    
    def _create_custom_generator(self):
        """Create custom signal generator from strategy code"""
        # This is a simplified implementation - in production you'd want 
        # proper sandboxing and security measures
        if not self.strategy.strategy_code:
            return None
        
        # For now, return a placeholder that could execute custom code
        return CustomSignalGenerator(self.strategy.strategy_code, self.parameters)
    
    async def generate_signals(self, symbols: List[str], lookback_days: int = 30) -> List[Dict[str, Any]]:
        """Generate trading signals based on market data from DataService"""
        signals = []
        
        # Get market data from DataService
        end_date = date.today()
        start_date = end_date - timedelta(days=lookback_days)
        
        # Ensure data is available for symbols
        availability = await self.data_service.ensure_data_available(symbols, lookback_days)
        available_symbols = [sym for sym, avail in availability.items() if avail]
        
        if not available_symbols:
            print(f"No market data available for symbols: {symbols}")
            return signals
        
        # Get market data
        market_data_dfs = await self.data_service.get_market_data(available_symbols, start_date, end_date)
        
        # Convert DataFrames to format expected by signal generators
        market_data = {}
        for symbol, df in market_data_dfs.items():
            if df is not None and not df.empty:
                market_data[symbol] = {
                    'open': df['Open'].tolist() if 'Open' in df.columns else [],
                    'high': df['High'].tolist() if 'High' in df.columns else [],
                    'low': df['Low'].tolist() if 'Low' in df.columns else [],
                    'close': df['Close'].tolist(),
                    'volume': df['Volume'].tolist() if 'Volume' in df.columns else [],
                    'dates': [d.strftime('%Y-%m-%d') for d in df.index],
                    'current_price': float(df['Close'].iloc[-1]),
                    'price_change': float(df['Close'].iloc[-1] - df['Close'].iloc[-2]) if len(df) > 1 else 0.0,
                    'price_change_percent': float((df['Close'].iloc[-1] - df['Close'].iloc[-2]) / df['Close'].iloc[-2] * 100) if len(df) > 1 else 0.0
                }
        
        # Generate signals using available generators
        for generator_name, generator in self.signal_generators.items():
            if generator and market_data:
                try:
                    generator_signals = await generator.generate_signals(market_data)
                    for signal in generator_signals:
                        signal["generator"] = generator_name
                        signal["strategy_id"] = self.strategy.id
                        signal["created_at"] = datetime.now(timezone.utc)
                        signals.append(signal)
                except Exception as e:
                    import traceback
                    print(f"Error in {generator_name} generator: {e}")
                    print(f"Traceback: {traceback.format_exc()}")
        
        return signals
    
    async def get_market_data_for_analysis(self, symbols: List[str], start_date: date, end_date: date) -> Dict[str, Any]:
        """Get market data for strategy analysis from DataService"""
        # Ensure data is available
        days_back = (end_date - start_date).days + 1
        availability = await self.data_service.ensure_data_available(symbols, days_back)
        
        available_symbols = [sym for sym, avail in availability.items() if avail]
        if not available_symbols:
            return {}
        
        # Get market data
        market_data_dfs = await self.data_service.get_market_data(available_symbols, start_date, end_date)
        
        # Convert to analysis format
        analysis_data = {}
        for symbol, df in market_data_dfs.items():
            if df is not None and not df.empty:
                analysis_data[symbol] = {
                    'symbol': symbol,
                    'data_points': len(df),
                    'start_date': df.index.min().strftime('%Y-%m-%d'),
                    'end_date': df.index.max().strftime('%Y-%m-%d'),
                    'price_range': {
                        'min': float(df['Close'].min()),
                        'max': float(df['Close'].max()),
                        'current': float(df['Close'].iloc[-1])
                    },
                    'volatility': float(df['Close'].pct_change().std()) if len(df) > 1 else 0.0,
                    'avg_volume': float(df['Volume'].mean()) if 'Volume' in df.columns else 0.0
                }
        
        return analysis_data
    
    async def analyze_strategy(self, symbols: List[str] = None) -> StrategyAnalysisResult:
        """Perform strategy analysis using real market data (no backtesting)"""
        
        # Validate strategy parameters
        param_validation = validate_strategy_parameters(self.parameters)
        if not param_validation["is_valid"]:
            return StrategyAnalysisResult(
                strategy_id=self.strategy.id,
                performance_metrics={},
                risk_metrics={},
                signal_analysis={},
                recommendations=[f"Fix parameter validation errors: {param_validation['errors']}"],
                analysis_timestamp=datetime.now(timezone.utc)
            )
        
        # Calculate risk metrics
        risk_metrics = calculate_strategy_risk_metrics(self.strategy, self.parameters)
        
        # Use default symbols if none provided
        if not symbols:
            symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA']  # Default test symbols
        
        # Generate signals to analyze strategy behavior
        recent_signals = await self.generate_signals(symbols, lookback_days=30)
        signal_analysis = await self._analyze_signal_quality(recent_signals)
        
        # Get market data for context
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        market_analysis = await self.get_market_data_for_analysis(symbols, start_date, end_date)
        
        # Performance analysis (theoretical, not backtested)
        performance_metrics = {
            "signals_generated": len(recent_signals),
            "symbols_analyzed": len([s for s in symbols if market_analysis.get(s)]),
            "market_data_availability": len([s for s in symbols if market_analysis.get(s)]) / len(symbols) * 100,
            "strategy_complexity_score": len(self.parameters),
            "avg_signal_confidence": sum(s.get('confidence_score', 0.5) for s in recent_signals) / max(len(recent_signals), 1),
            "data_coverage_days": 30,
            "market_context": market_analysis
        }
        
        # Generate recommendations
        recommendations = self._generate_recommendations(risk_metrics, signal_analysis, performance_metrics)
        
        return StrategyAnalysisResult(
            strategy_id=self.strategy.id,
            performance_metrics=performance_metrics,
            risk_metrics=risk_metrics,
            signal_analysis=signal_analysis,
            recommendations=recommendations,
            analysis_timestamp=datetime.now(timezone.utc)
        )
    
    async def _analyze_signal_quality(self, signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze the quality and characteristics of generated signals"""
        if not signals:
            return {
                "total_signals": 0,
                "signal_accuracy": Decimal("0.00"),
                "avg_confidence": Decimal("0.50"),
                "signal_frequency": "low",
                "signal_types": {"buy": 0, "sell": 0, "hold": 0},
                "symbols_with_signals": [],
                "generators_used": []
            }
        
        # Analyze signal distribution
        signal_types = {"buy": 0, "sell": 0, "hold": 0}
        confidence_scores = []
        symbols_with_signals = set()
        generators_used = set()
        
        for signal in signals:
            signal_type = signal.get('signal_type', 'hold')
            signal_types[signal_type] = signal_types.get(signal_type, 0) + 1
            confidence_scores.append(signal.get('confidence_score', 0.5))
            symbols_with_signals.add(signal.get('symbol', ''))
            generators_used.add(signal.get('generator', 'unknown'))
        
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.5
        
        # Determine signal frequency
        if len(signals) > 20:
            frequency = "high"
        elif len(signals) > 5:
            frequency = "medium"
        else:
            frequency = "low"
        
        return {
            "total_signals": len(signals),
            "signal_accuracy": Decimal("0.75"),  # Placeholder - would be calculated from historical performance
            "avg_confidence": Decimal(str(avg_confidence)),
            "signal_frequency": frequency,
            "signal_types": signal_types,
            "symbols_with_signals": list(symbols_with_signals),
            "unique_symbols_count": len(symbols_with_signals),
            "generators_used": list(generators_used)
        }
    
    def _generate_recommendations(
        self, 
        risk_metrics: Dict[str, Any], 
        signal_analysis: Dict[str, Any], 
        performance_metrics: Dict[str, Any]
    ) -> List[str]:
        """Generate strategy improvement recommendations"""
        recommendations = []
        
        # Risk-based recommendations
        if risk_metrics.get("risk_score", 0) > 0.7:
            recommendations.append("Consider reducing risk exposure by adjusting position sizing parameters")
        
        # Signal generation recommendations
        if signal_analysis.get("total_signals", 0) == 0:
            recommendations.append("Strategy is not generating signals - review signal generation logic and parameters")
        elif signal_analysis.get("signal_frequency") == "low":
            recommendations.append("Low signal frequency detected - consider adjusting sensitivity parameters")
        
        # Market data availability recommendations
        data_availability = performance_metrics.get("market_data_availability", 100)
        if data_availability < 80:
            recommendations.append(f"Market data availability is {data_availability:.1f}% - ensure DataService has required symbols")
        
        # Signal confidence recommendations
        avg_confidence = float(signal_analysis.get("avg_confidence", 0.5))
        if avg_confidence < 0.6:
            recommendations.append("Average signal confidence is low - review and tune strategy parameters")
        
        # Signal diversity recommendations
        signal_types = signal_analysis.get("signal_types", {})
        total_signals = sum(signal_types.values())
        if total_signals > 0:
            buy_ratio = signal_types.get("buy", 0) / total_signals
            if buy_ratio > 0.8:
                recommendations.append("Strategy heavily biased toward buy signals - review for balance")
            elif buy_ratio < 0.2:
                recommendations.append("Strategy heavily biased toward sell signals - review for balance")
        
        # Generator recommendations
        generators_used = signal_analysis.get("generators_used", [])
        if len(generators_used) == 0:
            recommendations.append("No signal generators are active - check strategy type and configuration")
        elif len(generators_used) == 1:
            recommendations.append("Only one signal generator active - consider diversifying signal sources")
        
        # Default recommendation if no specific issues found
        if not recommendations:
            recommendations.append("Strategy appears well-configured - continue monitoring with real market data")
        
        return recommendations
    
    async def optimize_parameters(self, optimization_target: str = "sharpe_ratio") -> Dict[str, Any]:
        """Optimize strategy parameters for a specific target metric"""
        # This would implement parameter optimization using techniques like:
        # - Grid search
        # - Genetic algorithms
        # - Bayesian optimization
        
        # For now, return a placeholder structure
        return {
            "optimization_target": optimization_target,
            "original_value": Decimal("1.25"),
            "optimized_value": Decimal("1.45"),
            "optimized_parameters": {
                param_name: param.current_value 
                for param_name, param in self.parameters.items()
            },
            "optimization_iterations": 100,
            "improvement_percentage": Decimal("16.00")
        }


class CustomSignalGenerator:
    """Signal generator for custom strategy code"""
    
    def __init__(self, strategy_code: str, parameters: Dict[str, StrategyParameter]):
        self.strategy_code = strategy_code
        self.parameters = parameters
    
    async def generate_signals(self, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute custom strategy code to generate signals"""
        # In production, this would need proper sandboxing and security
        # For now, return empty signals
        return []


# Strategy validation and health checks
async def validate_strategy(strategy: Strategy, parameters: List[StrategyParameter]) -> Dict[str, Any]:
    """Validate strategy configuration and parameters"""
    issues = []
    warnings = []
    
    # Basic strategy validation
    if not strategy.name:
        issues.append("Strategy name is required")
    
    if not strategy.strategy_type:
        issues.append("Strategy type is required")
    
    if strategy.strategy_type not in ["momentum", "mean_reversion", "arbitrage", "custom"]:
        issues.append(f"Invalid strategy type: {strategy.strategy_type}")
    
    # Parameter validation
    param_validation = validate_strategy_parameters({p.parameter_name: p for p in parameters})
    if not param_validation["is_valid"]:
        issues.extend(param_validation["errors"])
    
    # Custom strategy validation
    if strategy.strategy_type == "custom" and not strategy.strategy_code:
        issues.append("Custom strategy requires strategy code")
    
    # Risk level validation
    if strategy.risk_level not in ["low", "medium", "high"]:
        warnings.append(f"Unknown risk level: {strategy.risk_level}")
    
    return {
        "is_valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "validation_timestamp": datetime.now(timezone.utc)
    }