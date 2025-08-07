# core/backtesting_engine/engine.py
"""
Main backtesting engine - orchestrates the entire backtesting process
"""
import asyncio
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# NOTE: This core engine should NOT import from services directly
# Instead, it receives data through dependency injection from the service layer
# The BacktestingService will handle all service layer communication
from .portfolio import SimulationPortfolio, SimulationPosition, SimulationTransaction
from .execution import ExecutionEngine, OrderType, OrderStatus
from .metrics import PerformanceMetrics, RiskMetrics


@dataclass
class BacktestConfig:
    """Configuration for backtest execution"""
    start_date: datetime
    end_date: datetime
    initial_capital: Decimal
    symbols: List[str]
    commission_per_share: Decimal = Decimal("0.01")
    commission_percentage: Decimal = Decimal("0.0")
    slippage: Decimal = Decimal("0.001")  # 0.1% default
    
    # Risk management
    max_position_size: Optional[Decimal] = None  # Max % of portfolio per position
    max_daily_loss: Optional[Decimal] = None     # Max daily loss %
    
    # Execution settings
    execution_delay: int = 1  # Minutes delay between signal and execution
    market_impact: Decimal = Decimal("0.0005")  # Market impact per trade


@dataclass
class BacktestResult:
    """Results of a completed backtest"""
    backtest_id: str
    strategy_id: int
    config: BacktestConfig
    
    # Summary metrics
    total_return: Decimal
    return_percentage: Decimal
    sharpe_ratio: Decimal
    max_drawdown: Decimal
    volatility: Decimal
    
    # Trade statistics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: Decimal
    avg_trade_return: Decimal
    
    # Performance data
    daily_returns: List[Decimal]
    daily_portfolio_values: List[Decimal]
    trades: List[SimulationTransaction]
    positions: List[SimulationPosition]
    
    # Risk metrics
    risk_metrics: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    
    # Execution data
    start_time: datetime
    end_time: datetime
    execution_duration: float


class BacktestEngine:
    """
    Main backtesting engine that orchestrates strategy testing over historical periods
    Uses dependency injection for data and strategy logic - no direct service imports
    """
    
    def __init__(self, strategy_config: Dict[str, Any], strategy_parameters: Dict[str, Any]):
        self.strategy_config = strategy_config  # Strategy metadata
        self.parameters = strategy_parameters  # Strategy parameters
        # No direct service dependencies - data injected through method calls
        
    async def run_backtest(
        self, 
        config: BacktestConfig,
        market_data: Dict[str, Any],  # Pre-fetched by service layer
        strategy_executor: callable,  # Strategy execution function injected
        progress_callback: Optional[callable] = None
    ) -> BacktestResult:
        """
        Execute the complete backtest process
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            # Initialize components
            portfolio = SimulationPortfolio(config.initial_capital, "Backtest Portfolio")
            execution_engine = ExecutionEngine(config)
            performance_tracker = PerformanceMetrics()
            risk_tracker = RiskMetrics()
            
            if progress_callback:
                await progress_callback(15, "Processing market data and signals...")
            
            # Generate trading dates
            trading_dates = self._generate_trading_dates(config.start_date, config.end_date)
            total_dates = len(trading_dates)
            
            # Execute day-by-day simulation
            all_trades = []
            daily_metrics = []
            
            for i, current_date in enumerate(trading_dates):
                if progress_callback:
                    progress = 15 + int(70 * i / total_dates)
                    await progress_callback(progress, f"Processing {current_date.strftime('%Y-%m-%d')}...")
                
                # Get market data for current date
                daily_data = self._get_daily_market_data(market_data, current_date)
                
                # Generate signals using injected strategy executor
                signals = await strategy_executor(daily_data, current_date, self.parameters)
                
                # Execute trades based on signals
                daily_trades = await execution_engine.execute_signals(
                    signals, portfolio, daily_data
                )
                all_trades.extend(daily_trades)
                
                # Update portfolio with market prices  
                market_prices = {symbol: data["close"] for symbol, data in daily_data.items() if data}
                portfolio.update_market_prices(market_prices)
                
                # Calculate daily metrics
                daily_metric = performance_tracker.calculate_daily_metrics(
                    portfolio, daily_trades, current_date
                )
                daily_metrics.append(daily_metric)
                
                # Risk management checks
                if await self._check_risk_limits(portfolio, config, daily_metric):
                    break
            
            if progress_callback:
                await progress_callback(90, "Calculating final performance metrics...")
            
            # Calculate final performance metrics
            final_metrics = performance_tracker.calculate_final_metrics(
                daily_metrics, all_trades, config.initial_capital
            )
            
            risk_metrics = risk_tracker.calculate_risk_metrics(
                daily_metrics, all_trades
            )
            
            if progress_callback:
                await progress_callback(100, "Backtest completed successfully")
            
            # Create result object
            end_time = datetime.now(timezone.utc)
            
            return BacktestResult(
                backtest_id=f"bt_{int(start_time.timestamp())}",
                strategy_id=self.strategy_config.get("id", 0),
                config=config,
                total_return=final_metrics["total_return"],
                return_percentage=final_metrics["return_percentage"],
                sharpe_ratio=final_metrics["sharpe_ratio"],
                max_drawdown=final_metrics["max_drawdown"],
                volatility=final_metrics["volatility"],
                total_trades=len(all_trades),
                winning_trades=final_metrics["winning_trades"],
                losing_trades=final_metrics["losing_trades"],
                win_rate=final_metrics["win_rate"],
                avg_trade_return=final_metrics["avg_trade_return"],
                daily_returns=final_metrics["daily_returns"],
                daily_portfolio_values=final_metrics["daily_portfolio_values"],
                trades=all_trades,
                positions=portfolio.get_all_positions(),
                risk_metrics=risk_metrics,
                performance_metrics=final_metrics,
                start_time=start_time,
                end_time=end_time,
                execution_duration=(end_time - start_time).total_seconds()
            )
            
        except Exception as e:
            if progress_callback:
                await progress_callback(-1, f"Backtest failed: {str(e)}")
            raise
    
    # Market data fetching handled by service layer through dependency injection
    
    def _generate_trading_dates(self, start_date: datetime, end_date: datetime) -> List[datetime]:
        """Generate list of trading dates (exclude weekends)"""
        dates = []
        current = start_date
        
        while current <= end_date:
            # Skip weekends (0=Monday, 6=Sunday)
            if current.weekday() < 5:  # Monday-Friday
                dates.append(current)
            current = current + timedelta(days=1)  # Fixed: use timedelta for proper date arithmetic
        
        return dates
    
    def _get_daily_market_data(self, market_data: Dict[str, Any], date: datetime) -> Dict[str, Dict[str, Any]]:
        """Extract market data for specific date from pandas DataFrames"""
        daily_data = {}
        target_date = date.strftime("%Y-%m-%d")
        
        for symbol, df in market_data.items():
            if df is None or df.empty:
                continue
                
            # DataService returns pandas DataFrame with date index
            try:
                # Try different ways to access the date
                if hasattr(df, 'index') and len(df.index) > 0:
                    # Check if date is in index or columns
                    if target_date in df.index.astype(str):
                        row = df.loc[target_date]
                    elif 'date' in df.columns:
                        # Filter by date column
                        row_data = df[df['date'].astype(str).str.startswith(target_date)]
                        if not row_data.empty:
                            row = row_data.iloc[0]
                        else:
                            continue
                    else:
                        # Use first available row as fallback
                        row = df.iloc[0]
                    
                    daily_data[symbol] = {
                        "open": Decimal(str(row.get("open", row.get("Open", 0)))),
                        "high": Decimal(str(row.get("high", row.get("High", 0)))),
                        "low": Decimal(str(row.get("low", row.get("Low", 0)))),
                        "close": Decimal(str(row.get("close", row.get("Close", 0)))),
                        "volume": int(row.get("volume", row.get("Volume", 0))),
                        "date": date
                    }
            except Exception as e:
                print(f"Warning: Could not extract data for {symbol} on {target_date}: {e}")
                continue
        
        return daily_data
    
    # Signal generation handled by injected strategy executor from service layer
    
    async def _check_risk_limits(
        self, 
        portfolio: SimulationPortfolio, 
        config: BacktestConfig, 
        daily_metric: Dict[str, Any]
    ) -> bool:
        """Check if risk limits have been breached (returns True to stop backtest)"""
        
        # Check maximum daily loss
        if config.max_daily_loss and daily_metric.get("daily_return", 0) < -config.max_daily_loss:
            return True
        
        # Check maximum drawdown  
        if daily_metric.get("drawdown", 0) > Decimal("0.25"):  # 25% max drawdown
            return True
        
        # Check portfolio value hasn't gone to zero
        if portfolio.total_value <= Decimal("1000"):  # Stop if less than $1000 left
            return True
        
        return False