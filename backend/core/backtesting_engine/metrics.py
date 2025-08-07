# core/backtesting_engine/metrics.py
"""
Performance and risk metrics calculation for backtesting
"""
import math
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any, Optional
import statistics


class PerformanceMetrics:
    """
    Calculate comprehensive performance metrics for backtest results
    """
    
    def __init__(self):
        self.risk_free_rate = Decimal("0.02")  # 2% annual risk-free rate
    
    def calculate_daily_metrics(
        self,
        portfolio,
        daily_trades: List,
        date: datetime
    ) -> Dict[str, Any]:
        """Calculate daily performance metrics"""
        
        # Get previous day value for return calculation
        if portfolio.daily_snapshots:
            prev_value = portfolio.daily_snapshots[-1]["total_value"]
        else:
            prev_value = portfolio.initial_cash
        
        current_value = portfolio.total_value
        daily_return = (current_value - prev_value) / prev_value if prev_value > 0 else Decimal("0")
        daily_pnl = current_value - prev_value
        
        # Cumulative return
        cumulative_return = (current_value - portfolio.initial_cash) / portfolio.initial_cash if portfolio.initial_cash > 0 else Decimal("0")
        
        # Drawdown calculation
        if current_value > portfolio.peak_value:
            portfolio.peak_value = current_value
        
        drawdown = (portfolio.peak_value - current_value) / portfolio.peak_value if portfolio.peak_value > 0 else Decimal("0")
        
        return {
            "date": date,
            "portfolio_value": current_value,
            "cash_balance": portfolio.current_cash,
            "positions_value": portfolio.positions_value,
            "total_equity": current_value,
            "daily_return": daily_return,
            "daily_pnl": daily_pnl,
            "cumulative_return": cumulative_return,
            "drawdown": drawdown,
            "trades_executed": len(daily_trades),
            "positions_count": len(portfolio.positions)
        }
    
    def calculate_final_metrics(
        self,
        daily_metrics: List[Dict[str, Any]],
        all_trades: List,
        initial_capital: Decimal
    ) -> Dict[str, Any]:
        """Calculate comprehensive final performance metrics"""
        
        if not daily_metrics:
            return self._empty_metrics()
        
        # Basic performance
        final_value = daily_metrics[-1]["portfolio_value"]
        total_return = final_value - initial_capital
        return_percentage = (final_value / initial_capital - 1) if initial_capital > 0 else Decimal("0")
        
        # Daily returns for statistical calculations
        daily_returns = [float(metric["daily_return"]) for metric in daily_metrics if metric["daily_return"] != 0]
        portfolio_values = [float(metric["portfolio_value"]) for metric in daily_metrics]
        
        # Risk metrics
        volatility = Decimal(str(statistics.stdev(daily_returns))) if len(daily_returns) > 1 else Decimal("0")
        sharpe_ratio = self._calculate_sharpe_ratio(daily_returns, float(volatility))
        max_drawdown = max([float(metric["drawdown"]) for metric in daily_metrics], default=0)
        
        # Trade statistics
        trade_stats = self._calculate_trade_statistics(all_trades)
        
        # Time-based metrics
        trading_days = len(daily_metrics)
        annualized_return = self._annualize_return(float(return_percentage), trading_days)
        
        return {
            "total_return": total_return,
            "return_percentage": return_percentage,
            "annualized_return": Decimal(str(annualized_return)),
            "volatility": volatility,
            "annualized_volatility": volatility * Decimal(str(math.sqrt(252))),  # Annualized
            "sharpe_ratio": Decimal(str(sharpe_ratio)),
            "max_drawdown": Decimal(str(max_drawdown)),
            "trading_days": trading_days,
            "daily_returns": [Decimal(str(r)) for r in daily_returns],
            "daily_portfolio_values": [Decimal(str(v)) for v in portfolio_values],
            **trade_stats
        }
    
    def _calculate_sharpe_ratio(self, daily_returns: List[float], volatility: float) -> float:
        """Calculate Sharpe ratio"""
        if not daily_returns or volatility == 0:
            return 0.0
        
        avg_daily_return = statistics.mean(daily_returns)
        daily_risk_free_rate = float(self.risk_free_rate) / 252  # Daily risk-free rate
        
        excess_return = avg_daily_return - daily_risk_free_rate
        return (excess_return / volatility) * math.sqrt(252) if volatility > 0 else 0.0
    
    def _calculate_trade_statistics(self, all_trades: List) -> Dict[str, Any]:
        """Calculate trade-level statistics"""
        if not all_trades:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": Decimal("0"),
                "avg_trade_return": Decimal("0")
            }
        
        # Pair up buy/sell trades to calculate trade P&L
        trade_pnl = self._calculate_trade_pnl(all_trades)
        
        winning_trades = sum(1 for pnl in trade_pnl if pnl > 0)
        losing_trades = sum(1 for pnl in trade_pnl if pnl < 0)
        total_trades = len(trade_pnl)
        
        win_rate = Decimal(str(winning_trades / total_trades)) if total_trades > 0 else Decimal("0")
        avg_trade_return = Decimal(str(sum(trade_pnl) / total_trades)) if total_trades > 0 else Decimal("0")
        
        return {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate,
            "avg_trade_return": avg_trade_return
        }
    
    def _calculate_trade_pnl(self, all_trades: List) -> List[float]:
        """Calculate P&L for each round-trip trade"""
        # Simplified: calculate P&L based on buy/sell pairs
        # In a more sophisticated system, this would handle complex position tracking
        
        positions = {}  # Track open positions
        trade_pnl = []
        
        for trade in all_trades:
            symbol = trade.symbol
            
            if trade.transaction_type == "buy":
                if symbol not in positions:
                    positions[symbol] = []
                positions[symbol].append({
                    "quantity": float(trade.quantity),
                    "price": float(trade.price),
                    "fees": float(trade.fees)
                })
            
            elif trade.transaction_type == "sell" and symbol in positions:
                remaining_quantity = float(trade.quantity)
                sell_price = float(trade.price)
                sell_fees = float(trade.fees)
                
                while remaining_quantity > 0 and positions[symbol]:
                    buy_position = positions[symbol][0]
                    
                    # Calculate quantity to close
                    close_quantity = min(remaining_quantity, buy_position["quantity"])
                    
                    # Calculate P&L for this portion
                    pnl = (sell_price - buy_position["price"]) * close_quantity
                    pnl -= (buy_position["fees"] + sell_fees) * (close_quantity / float(trade.quantity))
                    
                    trade_pnl.append(pnl)
                    
                    # Update positions
                    buy_position["quantity"] -= close_quantity
                    remaining_quantity -= close_quantity
                    
                    if buy_position["quantity"] <= 0:
                        positions[symbol].pop(0)
                
                # Clean up empty position lists
                if not positions[symbol]:
                    del positions[symbol]
        
        return trade_pnl
    
    def _annualize_return(self, total_return_pct: float, trading_days: int) -> float:
        """Convert total return to annualized return"""
        if trading_days == 0:
            return 0.0
        
        years = trading_days / 252  # 252 trading days per year
        if years <= 0:
            return 0.0
        
        return ((1 + total_return_pct) ** (1 / years)) - 1
    
    def _empty_metrics(self) -> Dict[str, Any]:
        """Return empty metrics for failed backtests"""
        return {
            "total_return": Decimal("0"),
            "return_percentage": Decimal("0"),
            "annualized_return": Decimal("0"),
            "volatility": Decimal("0"),
            "annualized_volatility": Decimal("0"),
            "sharpe_ratio": Decimal("0"),
            "max_drawdown": Decimal("0"),
            "trading_days": 0,
            "daily_returns": [],
            "daily_portfolio_values": [],
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": Decimal("0"),
            "avg_trade_return": Decimal("0")
        }


class RiskMetrics:
    """
    Calculate risk metrics for backtesting
    """
    
    def calculate_risk_metrics(
        self,
        daily_metrics: List[Dict[str, Any]],
        all_trades: List
    ) -> Dict[str, Any]:
        """Calculate comprehensive risk metrics"""
        
        if not daily_metrics:
            return self._empty_risk_metrics()
        
        # Extract daily returns
        daily_returns = [float(metric["daily_return"]) for metric in daily_metrics]
        drawdowns = [float(metric["drawdown"]) for metric in daily_metrics]
        
        # Basic risk metrics
        max_drawdown = max(drawdowns, default=0)
        avg_drawdown = statistics.mean([d for d in drawdowns if d > 0]) if any(d > 0 for d in drawdowns) else 0
        
        # Volatility metrics
        volatility = statistics.stdev(daily_returns) if len(daily_returns) > 1 else 0
        downside_deviation = self._calculate_downside_deviation(daily_returns)
        
        # Risk ratios
        sortino_ratio = self._calculate_sortino_ratio(daily_returns, downside_deviation)
        calmar_ratio = self._calculate_calmar_ratio(daily_returns, max_drawdown)
        
        # Value at Risk (VaR)
        var_95 = self._calculate_var(daily_returns, 0.95)
        var_99 = self._calculate_var(daily_returns, 0.99)
        
        # Maximum consecutive losses
        max_consecutive_losses = self._calculate_max_consecutive_losses(daily_returns)
        
        return {
            "max_drawdown": max_drawdown,
            "avg_drawdown": avg_drawdown,
            "volatility": volatility,
            "annualized_volatility": volatility * math.sqrt(252),
            "downside_deviation": downside_deviation,
            "sortino_ratio": sortino_ratio,
            "calmar_ratio": calmar_ratio,
            "var_95": var_95,
            "var_99": var_99,
            "max_consecutive_losses": max_consecutive_losses
        }
    
    def _calculate_downside_deviation(self, returns: List[float]) -> float:
        """Calculate downside deviation (volatility of negative returns)"""
        negative_returns = [r for r in returns if r < 0]
        if len(negative_returns) < 2:
            return 0.0
        return statistics.stdev(negative_returns)
    
    def _calculate_sortino_ratio(self, returns: List[float], downside_deviation: float) -> float:
        """Calculate Sortino ratio (return/downside deviation)"""
        if downside_deviation == 0 or not returns:
            return 0.0
        
        avg_return = statistics.mean(returns)
        return (avg_return / downside_deviation) * math.sqrt(252)
    
    def _calculate_calmar_ratio(self, returns: List[float], max_drawdown: float) -> float:
        """Calculate Calmar ratio (annualized return / max drawdown)"""
        if max_drawdown == 0 or not returns:
            return 0.0
        
        annualized_return = statistics.mean(returns) * 252
        return annualized_return / max_drawdown
    
    def _calculate_var(self, returns: List[float], confidence: float) -> float:
        """Calculate Value at Risk at given confidence level"""
        if not returns:
            return 0.0
        
        sorted_returns = sorted(returns)
        index = int((1 - confidence) * len(sorted_returns))
        return sorted_returns[max(0, index)]
    
    def _calculate_max_consecutive_losses(self, returns: List[float]) -> int:
        """Calculate maximum number of consecutive losing days"""
        max_consecutive = 0
        current_consecutive = 0
        
        for return_val in returns:
            if return_val < 0:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
        
        return max_consecutive
    
    def _empty_risk_metrics(self) -> Dict[str, Any]:
        """Return empty risk metrics"""
        return {
            "max_drawdown": 0.0,
            "avg_drawdown": 0.0,
            "volatility": 0.0,
            "annualized_volatility": 0.0,
            "downside_deviation": 0.0,
            "sortino_ratio": 0.0,
            "calmar_ratio": 0.0,
            "var_95": 0.0,
            "var_99": 0.0,
            "max_consecutive_losses": 0
        }