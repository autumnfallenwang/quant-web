# services/backtesting_service.py
"""
Backtesting service layer - business logic for backtesting operations
Follows service layer pattern: handles data fetching, strategy coordination, and orchestration
"""
import asyncio
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any

from sqlmodel import select
from sqlalchemy import and_

from core.db import get_async_session_context
from models.db_models import (
    Backtest, BacktestTrade, BacktestDailyMetric, BacktestPosition,
    WorkspaceMembership
)
from core.backtesting_engine import BacktestEngine, BacktestConfig, BacktestResult
from services.data_service import DataService
from services.strategy_service import get_strategy, get_strategy_parameters
from services.job_service import create_job, update_job_status, update_job_progress


async def create_backtest(
    user_id: int,
    workspace_id: int,
    strategy_id: int,
    name: str,
    start_date: datetime,
    end_date: datetime,
    initial_capital: Decimal,
    symbols: Optional[List[str]] = None,
    description: Optional[str] = None,
    commission_per_share: Decimal = Decimal("0.01"),
    commission_percentage: Decimal = Decimal("0.0"),
    slippage: Decimal = Decimal("0.001")
) -> Backtest:
    """Create a new backtest configuration"""
    
    async with get_async_session_context() as session:
        # Verify workspace access
        workspace_query = select(WorkspaceMembership).where(
            and_(
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.user_profile_id == user_id
            )
        )
        workspace_membership = await session.exec(workspace_query)
        if not workspace_membership.first():
            raise ValueError("User does not have access to this workspace")
        
        # Verify strategy exists and user has access
        strategy = await get_strategy(strategy_id, user_id)
        if strategy.workspace_id != workspace_id:
            raise ValueError("Strategy does not belong to this workspace")
        
        # Use default symbols if none provided
        if not symbols:
            symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]  # Default backtest symbols
        
        # Create backtest record
        backtest = Backtest(
            name=name,
            description=description,
            strategy_id=strategy_id,
            workspace_id=workspace_id,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            symbols=symbols,
            commission_per_share=commission_per_share,
            commission_percentage=commission_percentage,
            slippage=slippage,
            status="pending",
            created_by=user_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        session.add(backtest)
        await session.commit()
        await session.refresh(backtest)
        
        return backtest


async def start_backtest(backtest_id: int, user_id: int) -> str:
    """Start backtest execution as a background job"""
    
    async with get_async_session_context() as session:
        # Get backtest with access check
        backtest = await get_backtest(backtest_id, user_id)
        
        if backtest.status != "pending":
            raise ValueError(f"Backtest is not in pending status (current: {backtest.status})")
        
        # Create background job
        job = await create_job(
            user_id=user_id,
            job_type="backtest_execution",
            workspace_id=backtest.workspace_id,
            priority="normal",
            metadata={
                "backtest_id": backtest_id,
                "backtest_name": backtest.name,
                "strategy_id": backtest.strategy_id,
                "symbols": backtest.symbols,
                "date_range": f"{backtest.start_date.date()} to {backtest.end_date.date()}"
            },
            estimated_duration=600  # 10 minutes estimate
        )
        
        # Update backtest status
        backtest.status = "running"
        backtest.job_id = job.job_id
        backtest.started_at = datetime.now(timezone.utc)
        backtest.updated_at = datetime.now(timezone.utc)
        
        session.add(backtest)
        await session.commit()
        
        # Start async processing
        asyncio.create_task(_execute_backtest(job.job_id, backtest_id, user_id))
        
        return job.job_id


async def get_backtest(backtest_id: int, user_id: int) -> Backtest:
    """Get backtest by ID with access control"""
    
    async with get_async_session_context() as session:
        # Get backtest with workspace membership check
        query = select(Backtest).join(
            WorkspaceMembership,
            and_(
                Backtest.workspace_id == WorkspaceMembership.workspace_id,
                WorkspaceMembership.user_profile_id == user_id
            )
        ).where(Backtest.id == backtest_id)
        
        result = await session.exec(query)
        backtest = result.first()
        
        if not backtest:
            raise ValueError("Backtest not found or access denied")
        
        return backtest


async def get_user_backtests(
    user_id: int,
    workspace_id: Optional[int] = None,
    strategy_id: Optional[int] = None,
    status: Optional[str] = None
) -> List[Backtest]:
    """Get backtests for a user with optional filtering"""
    
    async with get_async_session_context() as session:
        # Base query with workspace access check
        query = select(Backtest).join(
            WorkspaceMembership,
            and_(
                Backtest.workspace_id == WorkspaceMembership.workspace_id,
                WorkspaceMembership.user_profile_id == user_id
            )
        )
        
        # Apply filters
        if workspace_id:
            query = query.where(Backtest.workspace_id == workspace_id)
        
        if strategy_id:
            query = query.where(Backtest.strategy_id == strategy_id)
        
        if status:
            query = query.where(Backtest.status == status)
        
        # Order by created_at desc
        query = query.order_by(Backtest.created_at.desc())
        
        result = await session.exec(query)
        return result.all()


async def get_backtest_results(backtest_id: int, user_id: int) -> Dict[str, Any]:
    """Get comprehensive backtest results"""
    
    # Verify access
    backtest = await get_backtest(backtest_id, user_id)
    
    if backtest.status != "completed":
        return {"status": backtest.status, "message": "Backtest not completed yet"}
    
    async with get_async_session_context() as session:
        # Get trades
        trades_query = select(BacktestTrade).where(BacktestTrade.backtest_id == backtest_id)
        trades_result = await session.exec(trades_query)
        trades = trades_result.all()
        
        # Get daily metrics
        metrics_query = select(BacktestDailyMetric).where(
            BacktestDailyMetric.backtest_id == backtest_id
        ).order_by(BacktestDailyMetric.date)
        metrics_result = await session.exec(metrics_query)
        daily_metrics = metrics_result.all()
        
        # Get final positions
        positions_query = select(BacktestPosition).where(BacktestPosition.backtest_id == backtest_id)
        positions_result = await session.exec(positions_query)
        positions = positions_result.all()
        
        # Compile results
        return {
            "backtest_id": backtest.backtest_id,
            "name": backtest.name,
            "strategy_id": backtest.strategy_id,
            "status": backtest.status,
            "start_date": backtest.start_date,
            "end_date": backtest.end_date,
            "symbols": backtest.symbols,
            
            # Summary metrics
            "total_return": backtest.total_return,
            "return_percentage": backtest.return_percentage,
            "sharpe_ratio": backtest.sharpe_ratio,
            "max_drawdown": backtest.max_drawdown,
            "volatility": backtest.volatility,
            "total_trades": backtest.total_trades,
            "win_rate": backtest.win_rate,
            
            # Detailed data
            "trades": [_trade_to_dict(trade) for trade in trades],
            "daily_metrics": [_daily_metric_to_dict(metric) for metric in daily_metrics],
            "final_positions": [_position_to_dict(pos) for pos in positions],
            
            # Execution metadata
            "started_at": backtest.started_at,
            "completed_at": backtest.completed_at,
            "job_id": backtest.job_id
        }


async def cancel_backtest(backtest_id: int, user_id: int) -> bool:
    """Cancel a running backtest"""
    
    async with get_async_session_context() as session:
        backtest = await get_backtest(backtest_id, user_id)
        
        if backtest.status not in ["pending", "running"]:
            return False
        
        # Update status
        backtest.status = "cancelled"
        backtest.updated_at = datetime.now(timezone.utc)
        
        session.add(backtest)
        await session.commit()
        
        # Cancel associated job if exists
        if backtest.job_id:
            await update_job_status(backtest.job_id, "cancelled")
        
        return True


# =======================
# Background Job Functions
# =======================

async def _execute_backtest(job_id: str, backtest_id: int, user_id: int):
    """Background task for backtest execution"""
    try:
        await update_job_status(job_id, "running")
        await update_job_progress(job_id, 5, "Initializing backtest...")

        # Get backtest configuration
        backtest = await get_backtest(backtest_id, user_id)
        
        # Get strategy and parameters via service layer
        strategy = await get_strategy(backtest.strategy_id, user_id)
        parameters = await get_strategy_parameters(backtest.strategy_id, user_id)
        
        await update_job_progress(job_id, 10, "Fetching historical market data...")
        
        # Fetch market data via service layer
        data_service = DataService()
        market_data = await _fetch_historical_data(data_service, backtest)
        
        await update_job_progress(job_id, 20, "Setting up backtest engine...")
        
        # Create backtest configuration
        config = BacktestConfig(
            start_date=backtest.start_date,
            end_date=backtest.end_date,
            initial_capital=backtest.initial_capital,
            symbols=backtest.symbols,
            commission_per_share=backtest.commission_per_share,
            commission_percentage=backtest.commission_percentage,
            slippage=backtest.slippage
        )
        
        # Initialize backtest engine with dependency injection
        engine = BacktestEngine(
            strategy_config={"id": strategy.id, "type": strategy.strategy_type, "name": strategy.name},
            strategy_parameters={p.parameter_name: p.current_value for p in parameters}
        )
        
        await update_job_progress(job_id, 25, "Starting backtest execution...")
        
        # Create strategy executor function (dependency injection)
        async def strategy_executor(daily_data, date, params):
            return await _execute_strategy_logic(strategy, params, daily_data, date)
        
        # Progress callback
        async def progress_callback(progress, message):
            await update_job_progress(job_id, progress, message)
        
        # Execute backtest
        result = await engine.run_backtest(
            config=config,
            market_data=market_data,
            strategy_executor=strategy_executor,
            progress_callback=progress_callback
        )
        
        await update_job_progress(job_id, 95, "Saving backtest results...")
        
        # Save results to database
        await _save_backtest_results(backtest_id, result)
        
        await update_job_status(
            job_id, 
            "success", 
            {
                "progress_percent": 100,
                "progress_message": "Backtest completed successfully",
                "result": {
                    "total_return": float(result.total_return),
                    "return_percentage": float(result.return_percentage),
                    "sharpe_ratio": float(result.sharpe_ratio),
                    "max_drawdown": float(result.max_drawdown),
                    "total_trades": result.total_trades
                }
            }
        )

    except Exception as e:
        # Mark backtest as failed
        async with get_async_session_context() as session:
            backtest_query = select(Backtest).where(Backtest.id == backtest_id)
            backtest_result = await session.exec(backtest_query)
            backtest = backtest_result.first()
            
            if backtest:
                backtest.status = "failed"
                backtest.error_message = str(e)
                backtest.updated_at = datetime.now(timezone.utc)
                session.add(backtest)
                await session.commit()
        
        await update_job_status(
            job_id, 
            "failed", 
            {
                "error": str(e),
                "progress_message": f"Backtest failed: {str(e)}"
            }
        )


async def _fetch_historical_data(data_service: DataService, backtest: Backtest) -> Dict[str, Any]:
    """Fetch historical market data for backtest"""
    try:
        # Use the correct method: get_market_data
        market_data = await data_service.get_market_data(
            symbols=backtest.symbols,
            start_date=backtest.start_date.date(),
            end_date=backtest.end_date.date(),
            interval="1d"
        )
        return market_data
    except Exception as e:
        print(f"Error fetching market data: {e}")
        # Return empty data for all symbols
        return {symbol: None for symbol in backtest.symbols}


async def _execute_strategy_logic(
    strategy,
    strategy_parameters: Dict[str, str],
    daily_data: Dict[str, Dict[str, Any]], 
    date: datetime
) -> List[Dict[str, Any]]:
    """
    Execute strategy logic for backtesting
    This bridges to the Strategy Engine via service layer
    """
    signals = []
    
    # Get historical data for moving averages (this is a simplified version)
    # In production, this would call the Strategy Engine via service layer
    for symbol, data in daily_data.items():
        if data is None:
            continue
        
        signal = None
        current_price = data["close"]
        
        # Enhanced strategy implementations
        if strategy.strategy_type == "momentum":
            # More sensitive momentum strategy
            if current_price > data["open"] * Decimal("1.005"):  # 0.5% up (more sensitive)
                signal = {
                    "symbol": symbol,
                    "signal_type": "buy", 
                    "quantity": int(strategy_parameters.get("position_size", "100")),
                    "signal_strength": Decimal("0.8"),
                    "confidence_score": Decimal("0.7"),
                    "generated_at": date
                }
            elif current_price < data["open"] * Decimal("0.995"):  # 0.5% down
                signal = {
                    "symbol": symbol,
                    "signal_type": "sell",
                    "quantity": int(strategy_parameters.get("position_size", "100")),
                    "signal_strength": Decimal("0.8"),
                    "confidence_score": Decimal("0.7"),
                    "generated_at": date
                }
        
        elif strategy.strategy_type == "moving_average":
            # Simple Moving Average Crossover (simplified - uses daily high/low as proxy)
            # In real implementation, this would maintain historical price arrays
            daily_range = data["high"] - data["low"]
            mid_price = (data["high"] + data["low"]) / 2
            
            # Generate signals based on price position within daily range
            if current_price > mid_price * Decimal("1.01"):  # Price above mid-range
                signal = {
                    "symbol": symbol,
                    "signal_type": "buy",
                    "quantity": int(strategy_parameters.get("position_size", "100")),
                    "signal_strength": Decimal("0.7"),
                    "confidence_score": Decimal("0.6"),
                    "generated_at": date,
                    "reason": "Price above mid-range (MA proxy)"
                }
            elif current_price < mid_price * Decimal("0.99"):  # Price below mid-range  
                signal = {
                    "symbol": symbol,
                    "signal_type": "sell",
                    "quantity": int(strategy_parameters.get("position_size", "100")),
                    "signal_strength": Decimal("0.7"),
                    "confidence_score": Decimal("0.6"), 
                    "generated_at": date,
                    "reason": "Price below mid-range (MA proxy)"
                }
        
        elif strategy.strategy_type == "mean_reversion":
            # Aggressive mean reversion strategy - trades every day
            daily_range = data["high"] - data["low"]
            mid_price = (data["high"] + data["low"]) / 2
            
            # Buy when price is in lower 40% of daily range
            if current_price <= mid_price * Decimal("1.00"):  # At or below midpoint
                signal = {
                    "symbol": symbol,
                    "signal_type": "buy",  # Buy when price is low
                    "quantity": int(strategy_parameters.get("position_size", "50")),
                    "signal_strength": Decimal("0.7"),
                    "confidence_score": Decimal("0.6"),
                    "generated_at": date,
                    "reason": f"Mean reversion buy - price ${current_price} below mid ${mid_price}"
                }
            # Sell when price is in upper 60% of daily range  
            elif current_price >= mid_price * Decimal("1.00"):  # At or above midpoint
                signal = {
                    "symbol": symbol,
                    "signal_type": "sell",  # Sell when price is high
                    "quantity": int(strategy_parameters.get("position_size", "50")),
                    "signal_strength": Decimal("0.7"),
                    "confidence_score": Decimal("0.6"),
                    "generated_at": date,
                    "reason": f"Mean reversion sell - price ${current_price} above mid ${mid_price}"
                }
        
        if signal:
            signals.append(signal)
    
    return signals


async def _save_backtest_results(backtest_id: int, result: BacktestResult):
    """Save backtest results to database"""
    
    async with get_async_session_context() as session:
        # Update backtest record with results
        backtest_query = select(Backtest).where(Backtest.id == backtest_id)
        backtest_result = await session.exec(backtest_query)
        backtest = backtest_result.first()
        
        if not backtest:
            raise ValueError("Backtest not found")
        
        # Update summary metrics
        backtest.status = "completed"
        backtest.total_return = result.total_return
        backtest.return_percentage = result.return_percentage
        backtest.sharpe_ratio = result.sharpe_ratio
        backtest.max_drawdown = result.max_drawdown
        backtest.volatility = result.volatility
        backtest.total_trades = result.total_trades
        backtest.win_rate = result.win_rate
        backtest.completed_at = datetime.now(timezone.utc)
        backtest.updated_at = datetime.now(timezone.utc)
        
        session.add(backtest)
        
        # Save trades
        for trade in result.trades:
            db_trade = BacktestTrade(
                backtest_id=backtest_id,
                symbol=trade.symbol,
                trade_type=trade.transaction_type,
                quantity=int(trade.quantity),
                price=trade.price,
                commission=trade.fees,
                slippage=Decimal("0"),  # Calculated separately in execution engine
                signal_timestamp=trade.created_at,
                execution_timestamp=trade.executed_at,
                portfolio_value=Decimal("0"),  # Would be calculated from portfolio state
                cash_balance=Decimal("0"),     # Would be calculated from portfolio state
                position_size=0,               # Would be calculated from portfolio state
                signal_strength=trade.signal_strength,
                confidence_score=trade.confidence_score,
                created_at=datetime.now(timezone.utc)
            )
            session.add(db_trade)
        
        # Save daily metrics (simplified - using result data)
        for i, daily_value in enumerate(result.daily_portfolio_values):
            if i < len(result.daily_returns):
                daily_metric = BacktestDailyMetric(
                    backtest_id=backtest_id,
                    date=result.config.start_date + timedelta(days=i),
                    portfolio_value=daily_value,
                    cash_balance=Decimal("0"),  # Would track from portfolio
                    positions_value=Decimal("0"),  # Would track from portfolio
                    total_equity=daily_value,
                    daily_return=result.daily_returns[i],
                    daily_pnl=Decimal("0"),  # Would calculate from previous day
                    cumulative_return=((daily_value / result.config.initial_capital) - 1),
                    drawdown=Decimal("0"),  # Would track from peak
                    trades_executed=0,  # Would count daily trades
                    positions_count=0,  # Would count from portfolio
                    created_at=datetime.now(timezone.utc)
                )
                session.add(daily_metric)
        
        await session.commit()


# Helper functions for API responses
def _trade_to_dict(trade: BacktestTrade) -> Dict[str, Any]:
    """Convert BacktestTrade to dictionary"""
    return {
        "id": trade.id,
        "symbol": trade.symbol,
        "trade_type": trade.trade_type,
        "quantity": trade.quantity,
        "price": float(trade.price),
        "commission": float(trade.commission),
        "signal_timestamp": trade.signal_timestamp,
        "execution_timestamp": trade.execution_timestamp,
        "signal_strength": float(trade.signal_strength) if trade.signal_strength else None,
        "confidence_score": float(trade.confidence_score) if trade.confidence_score else None
    }


def _daily_metric_to_dict(metric: BacktestDailyMetric) -> Dict[str, Any]:
    """Convert BacktestDailyMetric to dictionary"""
    return {
        "date": metric.date,
        "portfolio_value": float(metric.portfolio_value),
        "daily_return": float(metric.daily_return),
        "cumulative_return": float(metric.cumulative_return),
        "drawdown": float(metric.drawdown),
        "trades_executed": metric.trades_executed,
        "positions_count": metric.positions_count
    }


def _position_to_dict(position: BacktestPosition) -> Dict[str, Any]:
    """Convert BacktestPosition to dictionary"""
    return {
        "symbol": position.symbol,
        "quantity": position.quantity,
        "avg_price": float(position.avg_price),
        "current_price": float(position.current_price),
        "market_value": float(position.market_value),
        "unrealized_pnl": float(position.unrealized_pnl),
        "total_pnl": float(position.total_pnl)
    }