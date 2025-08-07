# core/strategy_engine/calculations.py
"""
Strategy calculation utilities for performance metrics, risk analysis, and parameter validation
"""
import math
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Any, Tuple

from models.db_models import Strategy, StrategyParameter


def calculate_strategy_performance(
    trades: List[Dict[str, Any]], 
    initial_capital: Decimal, 
    final_capital: Decimal
) -> Dict[str, Any]:
    """Calculate comprehensive strategy performance metrics"""
    
    if not trades:
        return {
            "total_return": Decimal("0.00"),
            "return_percentage": Decimal("0.00"),
            "sharpe_ratio": None,
            "max_drawdown": None,
            "win_rate": None,
            "avg_trade_return": None,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0
        }
    
    # Basic return calculations
    total_return = final_capital - initial_capital
    return_percentage = (total_return / initial_capital * 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    # Trade analysis
    winning_trades = 0
    losing_trades = 0
    trade_returns = []
    
    for trade in trades:
        trade_return = trade.get("return", Decimal("0.00"))
        trade_returns.append(trade_return)
        
        if trade_return > 0:
            winning_trades += 1
        else:
            losing_trades += 1
    
    # Win rate calculation
    total_trades = len(trades)
    win_rate = (Decimal(winning_trades) / Decimal(total_trades)).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP) if total_trades > 0 else None
    
    # Average trade return
    avg_trade_return = (sum(trade_returns) / Decimal(total_trades)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) if total_trades > 0 else None
    
    # Sharpe ratio calculation (simplified)
    if trade_returns:
        returns_mean = sum(trade_returns) / len(trade_returns)
        returns_variance = sum((r - returns_mean) ** 2 for r in trade_returns) / len(trade_returns)
        returns_std = Decimal(str(math.sqrt(float(returns_variance))))
        
        # Assume risk-free rate of 2% annually
        risk_free_rate = Decimal("0.02")
        sharpe_ratio = ((returns_mean - risk_free_rate) / returns_std).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) if returns_std > 0 else None
    else:
        sharpe_ratio = None
    
    # Max drawdown calculation (simplified)
    max_drawdown = calculate_max_drawdown(trades)
    
    return {
        "total_return": total_return,
        "return_percentage": return_percentage,
        "sharpe_ratio": sharpe_ratio,
        "max_drawdown": max_drawdown,
        "win_rate": win_rate,
        "avg_trade_return": avg_trade_return,
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades
    }


def calculate_max_drawdown(trades: List[Dict[str, Any]]) -> Optional[Decimal]:
    """Calculate maximum drawdown from trade history"""
    if not trades:
        return None
    
    # Calculate cumulative returns
    cumulative_return = Decimal("0.00")
    peak = Decimal("0.00")
    max_drawdown = Decimal("0.00")
    
    for trade in trades:
        trade_return = trade.get("return", Decimal("0.00"))
        cumulative_return += trade_return
        
        # Update peak
        if cumulative_return > peak:
            peak = cumulative_return
        
        # Calculate drawdown
        drawdown = peak - cumulative_return
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    
    return max_drawdown.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calculate_strategy_risk_metrics(
    strategy: Strategy, 
    parameters: Dict[str, StrategyParameter]
) -> Dict[str, Any]:
    """Calculate risk metrics for a strategy"""
    
    # Base risk score based on strategy type
    risk_scores = {
        "momentum": Decimal("0.6"),      # Medium-high risk
        "mean_reversion": Decimal("0.4"), # Medium risk  
        "arbitrage": Decimal("0.2"),     # Low risk
        "custom": Decimal("0.5")         # Medium risk (unknown)
    }
    
    base_risk = risk_scores.get(strategy.strategy_type, Decimal("0.5"))
    
    # Adjust risk based on risk level setting
    risk_multipliers = {
        "low": Decimal("0.7"),
        "medium": Decimal("1.0"),
        "high": Decimal("1.3")
    }
    
    risk_multiplier = risk_multipliers.get(strategy.risk_level, Decimal("1.0"))
    risk_score = (base_risk * risk_multiplier).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    # Ensure risk score stays within bounds
    risk_score = min(max(risk_score, Decimal("0.00")), Decimal("1.00"))
    
    # Parameter-based risk adjustments
    parameter_risk = calculate_parameter_risk(parameters)
    
    # Final risk score
    final_risk_score = ((risk_score + parameter_risk) / 2).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    # Risk classification
    if final_risk_score <= Decimal("0.3"):
        risk_level = "low"
    elif final_risk_score <= Decimal("0.7"):
        risk_level = "medium"
    else:
        risk_level = "high"
    
    return {
        "risk_score": final_risk_score,
        "risk_level": risk_level,
        "base_risk": base_risk,
        "parameter_risk": parameter_risk,
        "risk_factors": {
            "strategy_type": strategy.strategy_type,
            "configured_risk_level": strategy.risk_level,
            "parameter_complexity": len(parameters)
        }
    }


def calculate_parameter_risk(parameters: Dict[str, StrategyParameter]) -> Decimal:
    """Calculate risk contribution from strategy parameters"""
    if not parameters:
        return Decimal("0.50")  # Default medium risk for no parameters
    
    risk_factors = []
    
    for param_name, param in parameters.items():
        # Risk based on parameter type and values
        if param.parameter_type in ["float", "int"]:
            try:
                current_val = Decimal(param.current_value)
                
                # Parameters that might indicate higher risk
                if "leverage" in param_name.lower():
                    # Higher leverage = higher risk
                    risk_factors.append(min(current_val / 10, Decimal("1.0")))
                elif "stop_loss" in param_name.lower():
                    # Wider stop loss = higher risk
                    risk_factors.append(current_val / 100)
                elif "position_size" in param_name.lower():
                    # Larger position size = higher risk
                    risk_factors.append(current_val / 100)
                else:
                    # Default parameter risk
                    risk_factors.append(Decimal("0.1"))
                    
            except (ValueError, TypeError):
                # If we can't parse the value, assume medium risk
                risk_factors.append(Decimal("0.5"))
        else:
            # Boolean/string parameters have lower risk
            risk_factors.append(Decimal("0.1"))
    
    # Average risk from all parameters
    if risk_factors:
        avg_risk = sum(risk_factors) / len(risk_factors)
        return min(avg_risk, Decimal("1.0")).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    return Decimal("0.50")


def validate_strategy_parameters(parameters: Dict[str, StrategyParameter]) -> Dict[str, Any]:
    """Validate strategy parameters for correctness and consistency"""
    errors = []
    warnings = []
    
    for param_name, param in parameters.items():
        # Validate required parameters
        if param.is_required and not param.current_value:
            errors.append(f"Required parameter '{param_name}' has no value")
            continue
        
        # Type-specific validation
        if param.parameter_type == "int":
            try:
                int_val = int(param.current_value)
                
                # Check bounds
                if param.min_value and int_val < int(param.min_value):
                    errors.append(f"Parameter '{param_name}' value {int_val} is below minimum {param.min_value}")
                if param.max_value and int_val > int(param.max_value):
                    errors.append(f"Parameter '{param_name}' value {int_val} is above maximum {param.max_value}")
                    
            except (ValueError, TypeError):
                errors.append(f"Parameter '{param_name}' should be an integer, got '{param.current_value}'")
        
        elif param.parameter_type == "float":
            try:
                float_val = float(param.current_value)
                
                # Check bounds
                if param.min_value and float_val < float(param.min_value):
                    errors.append(f"Parameter '{param_name}' value {float_val} is below minimum {param.min_value}")
                if param.max_value and float_val > float(param.max_value):
                    errors.append(f"Parameter '{param_name}' value {float_val} is above maximum {param.max_value}")
                    
            except (ValueError, TypeError):
                errors.append(f"Parameter '{param_name}' should be a float, got '{param.current_value}'")
        
        elif param.parameter_type == "boolean":
            if param.current_value.lower() not in ["true", "false", "1", "0"]:
                errors.append(f"Parameter '{param_name}' should be boolean (true/false), got '{param.current_value}'")
        
        # Parameter-specific business logic validation
        if param_name.lower() == "leverage" and param.parameter_type in ["int", "float"]:
            try:
                leverage_val = float(param.current_value)
                if leverage_val > 10:
                    warnings.append(f"High leverage ({leverage_val}x) increases risk significantly")
                elif leverage_val < 1:
                    errors.append("Leverage cannot be less than 1")
            except (ValueError, TypeError):
                pass  # Already caught in type validation
    
    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "validated_at": datetime.now(timezone.utc)
    }


def evaluate_strategy_signals(signals: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Evaluate the quality and characteristics of strategy signals"""
    if not signals:
        return {
            "total_signals": 0,
            "signal_distribution": {"buy": 0, "sell": 0, "hold": 0},
            "avg_confidence": Decimal("0.00"),
            "avg_strength": Decimal("0.00"),
            "signal_quality": "unknown"
        }
    
    # Count signal types
    signal_counts = {"buy": 0, "sell": 0, "hold": 0}
    confidence_scores = []
    strength_scores = []
    
    for signal in signals:
        signal_type = signal.get("signal_type", "hold")
        if signal_type in signal_counts:
            signal_counts[signal_type] += 1
        
        confidence = signal.get("confidence_score", Decimal("0.5"))
        strength = signal.get("signal_strength", Decimal("0.5"))
        
        confidence_scores.append(confidence)
        strength_scores.append(strength)
    
    # Calculate averages
    avg_confidence = (sum(confidence_scores) / len(confidence_scores)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    avg_strength = (sum(strength_scores) / len(strength_scores)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    # Determine signal quality
    quality_score = (avg_confidence + avg_strength) / 2
    if quality_score >= Decimal("0.8"):
        signal_quality = "excellent"
    elif quality_score >= Decimal("0.6"):
        signal_quality = "good"
    elif quality_score >= Decimal("0.4"):
        signal_quality = "fair"
    else:
        signal_quality = "poor"
    
    return {
        "total_signals": len(signals),
        "signal_distribution": signal_counts,
        "avg_confidence": avg_confidence,
        "avg_strength": avg_strength,
        "signal_quality": signal_quality,
        "quality_score": quality_score
    }


def calculate_correlation_matrix(strategies: List[Strategy]) -> Dict[str, Any]:
    """Calculate correlation matrix between strategies (placeholder for future implementation)"""
    # This would calculate correlations between strategy returns
    # For now, return a placeholder structure
    
    strategy_names = [s.name for s in strategies]
    
    # Create identity matrix as placeholder
    correlation_matrix = {}
    for i, strategy1 in enumerate(strategy_names):
        correlation_matrix[strategy1] = {}
        for j, strategy2 in enumerate(strategy_names):
            if i == j:
                correlation_matrix[strategy1][strategy2] = Decimal("1.00")
            else:
                # Placeholder correlation (would be calculated from actual returns)
                correlation_matrix[strategy1][strategy2] = Decimal("0.25")
    
    return {
        "correlation_matrix": correlation_matrix,
        "strategies": strategy_names,
        "calculated_at": datetime.now(timezone.utc)
    }