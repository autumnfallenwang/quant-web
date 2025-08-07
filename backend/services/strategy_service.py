# services/strategy_service.py
"""
Strategy service layer - business logic for strategy management, analysis, and signal generation
"""
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Any

from sqlmodel import select
from sqlalchemy import and_

from core.db import get_async_session_context
from models.db_models import (
    Strategy, StrategyParameter, Signal, StrategyPerformance,
    WorkspaceMembership
)
from core.strategy_engine import (
    StrategyEngine, validate_strategy
)
from services.job_service import create_job, update_job_status, update_job_progress


async def create_strategy(
    user_id: int,
    workspace_id: int,
    name: str,
    strategy_type: str,
    description: Optional[str] = None,
    strategy_code: Optional[str] = None,
    risk_level: str = "medium",
    is_public: bool = False,
    parameters: Optional[List[Dict[str, Any]]] = None
) -> Strategy:
    """Create a new trading strategy"""
    
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
        
        # Create strategy
        strategy = Strategy(
            name=name,
            description=description,
            strategy_type=strategy_type,
            strategy_code=strategy_code,
            risk_level=risk_level,
            is_public=is_public,
            workspace_id=workspace_id,
            created_by=user_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        session.add(strategy)
        await session.flush()
        await session.refresh(strategy)
        
        # Create strategy parameters if provided
        if parameters:
            for param_data in parameters:
                parameter = StrategyParameter(
                    strategy_id=strategy.id,
                    parameter_name=param_data["name"],
                    parameter_type=param_data["type"],
                    default_value=param_data.get("default_value", ""),
                    current_value=param_data.get("current_value", param_data.get("default_value", "")),
                    min_value=param_data.get("min_value"),
                    max_value=param_data.get("max_value"),
                    description=param_data.get("description"),
                    is_required=param_data.get("is_required", True),
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                session.add(parameter)
        
        await session.commit()
        await session.refresh(strategy)
        
        return strategy


async def get_strategy(strategy_id: int, user_id: int) -> Strategy:
    """Get strategy by ID with access control"""
    
    async with get_async_session_context() as session:
        # Get strategy with workspace membership check
        query = select(Strategy).join(
            WorkspaceMembership,
            and_(
                Strategy.workspace_id == WorkspaceMembership.workspace_id,
                WorkspaceMembership.user_profile_id == user_id
            )
        ).where(Strategy.id == strategy_id)
        
        result = await session.exec(query)
        strategy = result.first()
        
        if not strategy:
            raise ValueError("Strategy not found or access denied")
        
        return strategy


async def get_user_strategies(
    user_id: int, 
    workspace_id: Optional[int] = None,
    strategy_type: Optional[str] = None,
    is_active: Optional[bool] = None
) -> List[Strategy]:
    """Get strategies for a user with optional filtering"""
    
    async with get_async_session_context() as session:
        # Base query with workspace access check
        query = select(Strategy).join(
            WorkspaceMembership,
            and_(
                Strategy.workspace_id == WorkspaceMembership.workspace_id,
                WorkspaceMembership.user_profile_id == user_id
            )
        )
        
        # Apply filters
        if workspace_id:
            query = query.where(Strategy.workspace_id == workspace_id)
        
        if strategy_type:
            query = query.where(Strategy.strategy_type == strategy_type)
        
        if is_active is not None:
            query = query.where(Strategy.is_active == is_active)
        
        # Order by updated_at desc
        query = query.order_by(Strategy.updated_at.desc())
        
        result = await session.exec(query)
        return result.all()


async def update_strategy(
    strategy_id: int,
    user_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    strategy_code: Optional[str] = None,
    risk_level: Optional[str] = None,
    is_active: Optional[bool] = None
) -> Strategy:
    """Update strategy details"""
    
    async with get_async_session_context() as session:
        # Get strategy with access check
        strategy = await get_strategy(strategy_id, user_id)
        
        # Update fields
        if name is not None:
            strategy.name = name
        if description is not None:
            strategy.description = description
        if strategy_code is not None:
            strategy.strategy_code = strategy_code
        if risk_level is not None:
            strategy.risk_level = risk_level
        if is_active is not None:
            strategy.is_active = is_active
        
        strategy.updated_at = datetime.now(timezone.utc)
        
        session.add(strategy)
        await session.commit()
        await session.refresh(strategy)
        
        return strategy


async def get_strategy_parameters(strategy_id: int, user_id: int) -> List[StrategyParameter]:
    """Get parameters for a strategy"""
    
    # Verify strategy access
    await get_strategy(strategy_id, user_id)
    
    async with get_async_session_context() as session:
        query = select(StrategyParameter).where(
            StrategyParameter.strategy_id == strategy_id
        ).order_by(StrategyParameter.parameter_name)
        
        result = await session.exec(query)
        return result.all()


async def update_strategy_parameter(
    strategy_id: int,
    user_id: int,
    parameter_name: str,
    current_value: str
) -> StrategyParameter:
    """Update a strategy parameter value"""
    
    # Verify strategy access
    await get_strategy(strategy_id, user_id)
    
    async with get_async_session_context() as session:
        query = select(StrategyParameter).where(
            and_(
                StrategyParameter.strategy_id == strategy_id,
                StrategyParameter.parameter_name == parameter_name
            )
        )
        
        result = await session.exec(query)
        parameter = result.first()
        
        if not parameter:
            raise ValueError(f"Parameter '{parameter_name}' not found for strategy")
        
        parameter.current_value = current_value
        parameter.updated_at = datetime.now(timezone.utc)
        
        session.add(parameter)
        await session.commit()
        await session.refresh(parameter)
        
        return parameter


async def analyze_strategy_quick(strategy_id: int, user_id: int, symbols: Optional[List[str]] = None) -> Dict[str, Any]:
    """Perform quick strategy analysis using real market data"""
    
    async with get_async_session_context() as session:
        # Get strategy and parameters
        strategy = await get_strategy(strategy_id, user_id)
        parameters = await get_strategy_parameters(strategy_id, user_id)
        
        # Create strategy engine with DataService integration
        engine = StrategyEngine(strategy, parameters)
        
        # Use default symbols if none provided
        if not symbols:
            symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA']  # Default analysis symbols
        
        # Perform analysis with real market data
        analysis_result = await engine.analyze_strategy(symbols)
        
        return {
            "strategy_id": analysis_result.strategy_id,
            "performance_metrics": analysis_result.performance_metrics,
            "risk_metrics": analysis_result.risk_metrics,
            "signal_analysis": analysis_result.signal_analysis,
            "recommendations": analysis_result.recommendations,
            "analysis_timestamp": analysis_result.analysis_timestamp,
            "symbols_analyzed": symbols
        }


async def analyze_strategy_comprehensive(strategy_id: int, user_id: int, symbols: Optional[List[str]] = None) -> str:
    """Start comprehensive strategy analysis as a job"""
    
    # Verify strategy access
    strategy = await get_strategy(strategy_id, user_id)
    
    # Use default symbols if none provided
    if not symbols:
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'BRK-B', 'UNH', 'JNJ']
    
    # Create job for comprehensive analysis
    job = await create_job(
        user_id=user_id,
        job_type="strategy_analysis_comprehensive",
        workspace_id=strategy.workspace_id,
        priority="normal",
        metadata={
            "strategy_id": strategy_id,
            "strategy_name": strategy.name,
            "analysis_type": "comprehensive",
            "symbols": symbols  # Store symbols in job metadata
        },
        estimated_duration=300  # 5 minutes
    )
    
    # Start async processing with symbols
    asyncio.create_task(_process_comprehensive_analysis(job.job_id, strategy_id, user_id, symbols))
    
    return job.job_id


async def backtest_strategy(
    strategy_id: int,
    user_id: int,
    start_date: datetime,
    end_date: datetime,
    initial_capital: Decimal = Decimal("100000.00")
) -> str:
    """Start strategy backtesting as a job - DEPRECATED: Backtesting moved to separate Backtesting Engine"""
    
    # This function is deprecated but kept for API compatibility
    # In production, this would delegate to the Backtesting Engine
    
    raise NotImplementedError(
        "Backtesting has been moved to a separate Backtesting Engine. "
        "Use the Backtesting Engine API endpoints instead. "
        "This method is kept for backwards compatibility but no longer functional."
    )


async def generate_strategy_signals(
    strategy_id: int,
    user_id: int,
    symbols: List[str],
    lookback_days: int = 30
) -> List[Dict[str, Any]]:
    """Generate trading signals using the strategy with real market data from DataService"""
    
    async with get_async_session_context() as session:
        # Get strategy and parameters
        strategy = await get_strategy(strategy_id, user_id)
        parameters = await get_strategy_parameters(strategy_id, user_id)
        
        # Create strategy engine with DataService integration
        engine = StrategyEngine(strategy, parameters)
        
        # Generate signals using real market data
        signals = await engine.generate_signals(symbols, lookback_days)
        
        # Store signals in database
        for signal_data in signals:
            # Convert Decimal values to strings for JSON serialization
            json_signal_data = {}
            for key, value in signal_data.get("signal_data", {}).items():
                if isinstance(value, Decimal):
                    json_signal_data[key] = str(value)
                else:
                    json_signal_data[key] = value
            
            signal = Signal(
                strategy_id=strategy_id,
                signal_type=signal_data.get("signal_type", "hold"),
                symbol=signal_data.get("symbol", "UNKNOWN"),
                signal_strength=signal_data.get("signal_strength", Decimal("0.5")),
                price=signal_data.get("price", Decimal("0.0")),
                confidence_score=signal_data.get("confidence_score", Decimal("0.5")),
                signal_data=json_signal_data,
                created_at=signal_data.get("created_at", datetime.now(timezone.utc))
            )
            session.add(signal)
        
        await session.commit()
        
        return signals


async def get_strategy_signals(
    strategy_id: int,
    user_id: int,
    limit: int = 50,
    signal_type: Optional[str] = None,
    symbol: Optional[str] = None
) -> List[Signal]:
    """Get signals generated by a strategy"""
    
    # Verify strategy access
    await get_strategy(strategy_id, user_id)
    
    async with get_async_session_context() as session:
        query = select(Signal).where(Signal.strategy_id == strategy_id)
        
        # Apply filters
        if signal_type:
            query = query.where(Signal.signal_type == signal_type)
        if symbol:
            query = query.where(Signal.symbol == symbol)
        
        # Order by created_at desc and limit
        query = query.order_by(Signal.created_at.desc()).limit(limit)
        
        result = await session.exec(query)
        return result.all()


async def get_strategy_performance(
    strategy_id: int,
    user_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[StrategyPerformance]:
    """Get strategy performance records"""
    
    # Verify strategy access
    await get_strategy(strategy_id, user_id)
    
    async with get_async_session_context() as session:
        query = select(StrategyPerformance).where(StrategyPerformance.strategy_id == strategy_id)
        
        # Apply date filters
        if start_date:
            query = query.where(StrategyPerformance.period_start >= start_date)
        if end_date:
            query = query.where(StrategyPerformance.period_end <= end_date)
        
        # Order by period_start desc
        query = query.order_by(StrategyPerformance.period_start.desc())
        
        result = await session.exec(query)
        return result.all()


async def validate_strategy_config(strategy_id: int, user_id: int) -> Dict[str, Any]:
    """Validate strategy configuration and parameters"""
    
    async with get_async_session_context() as session:
        # Get strategy and parameters
        strategy = await get_strategy(strategy_id, user_id)
        parameters = await get_strategy_parameters(strategy_id, user_id)
        
        # Validate using strategy engine
        validation_result = await validate_strategy(strategy, parameters)
        
        return validation_result


async def clone_strategy(
    strategy_id: int,
    user_id: int,
    new_name: str,
    target_workspace_id: Optional[int] = None
) -> Strategy:
    """Clone an existing strategy"""
    
    async with get_async_session_context() as session:
        # Get original strategy
        original_strategy = await get_strategy(strategy_id, user_id)
        original_parameters = await get_strategy_parameters(strategy_id, user_id)
        
        # Use original workspace if target not specified
        workspace_id = target_workspace_id or original_strategy.workspace_id
        
        # Verify target workspace access
        workspace_query = select(WorkspaceMembership).where(
            and_(
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.user_profile_id == user_id
            )
        )
        workspace_membership = await session.exec(workspace_query)
        if not workspace_membership.first():
            raise ValueError("User does not have access to target workspace")
        
        # Create cloned strategy
        cloned_strategy = Strategy(
            name=new_name,
            description=f"Cloned from: {original_strategy.name}",
            strategy_type=original_strategy.strategy_type,
            strategy_code=original_strategy.strategy_code,
            risk_level=original_strategy.risk_level,
            is_public=False,  # Cloned strategies start as private
            workspace_id=workspace_id,
            created_by=user_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        session.add(cloned_strategy)
        await session.flush()
        await session.refresh(cloned_strategy)
        
        # Clone parameters
        for original_param in original_parameters:
            cloned_param = StrategyParameter(
                strategy_id=cloned_strategy.id,
                parameter_name=original_param.parameter_name,
                parameter_type=original_param.parameter_type,
                default_value=original_param.default_value,
                current_value=original_param.current_value,
                min_value=original_param.min_value,
                max_value=original_param.max_value,
                description=original_param.description,
                is_required=original_param.is_required,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            session.add(cloned_param)
        
        await session.commit()
        await session.refresh(cloned_strategy)
        
        return cloned_strategy


async def get_public_strategies(
    user_id: int,
    strategy_type: Optional[str] = None,
    limit: int = 50
) -> List[Strategy]:
    """Get public strategies that can be cloned"""
    
    async with get_async_session_context() as session:
        query = select(Strategy).where(
            and_(
                Strategy.is_public == True,
                Strategy.is_active == True,
                Strategy.created_by != user_id  # Exclude user's own strategies
            )
        )
        
        # Apply filters
        if strategy_type:
            query = query.where(Strategy.strategy_type == strategy_type)
        
        # Order by created_at desc and limit
        query = query.order_by(Strategy.created_at.desc()).limit(limit)
        
        result = await session.exec(query)
        return result.all()


# Background job functions for long-running operations
async def execute_comprehensive_analysis_job(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """Execute comprehensive strategy analysis job"""
    
    strategy_id = job_data["strategy_id"]
    
    async with get_async_session_context() as session:
        # Get strategy and parameters (bypass user check for background job)
        strategy_query = select(Strategy).where(Strategy.id == strategy_id)
        strategy_result = await session.exec(strategy_query)
        strategy = strategy_result.first()
        
        if not strategy:
            raise ValueError("Strategy not found")
        
        parameters_query = select(StrategyParameter).where(StrategyParameter.strategy_id == strategy_id)
        parameters_result = await session.exec(parameters_query)
        parameters = parameters_result.all()
        
        # Create strategy engine and perform analysis
        engine = StrategyEngine(strategy, parameters)
        analysis_result = await engine.analyze_strategy(include_backtest=True)
        
        return {
            "strategy_analysis": {
                "strategy_id": analysis_result.strategy_id,
                "performance_metrics": analysis_result.performance_metrics,
                "risk_metrics": analysis_result.risk_metrics,
                "signal_analysis": analysis_result.signal_analysis,
                "recommendations": analysis_result.recommendations,
                "analysis_timestamp": analysis_result.analysis_timestamp.isoformat()
            },
            "analysis_completed": True
        }


async def execute_backtest_job(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """Execute strategy backtesting job - DEPRECATED: Moved to Backtesting Engine"""
    
    # This function is deprecated but kept for job system compatibility
    # In production, this would delegate to the Backtesting Engine
    
    raise NotImplementedError(
        "Backtesting has been moved to a separate Backtesting Engine. "
        "This job type should no longer be created. "
        "Update job creation logic to use Backtesting Engine instead."
    )


# ===============================
# Background Processing Functions  
# ===============================

async def _process_comprehensive_analysis(job_id: str, strategy_id: int, user_id: int, symbols: Optional[List[str]] = None):
    """Background task for comprehensive strategy analysis"""
    try:
        await update_job_status(job_id, "running")
        await update_job_progress(job_id, 10, "Fetching strategy data")

        # Get strategy and related data
        strategy = await get_strategy(strategy_id, user_id)
        parameters = await get_strategy_parameters(strategy_id, user_id)
        signals = await get_strategy_signals(strategy_id, user_id)
        performance_records = await get_strategy_performance(strategy_id, user_id)

        await update_job_progress(job_id, 30, "Running basic analysis")

        # Run comprehensive analysis using strategy engine with real market data
        engine = StrategyEngine(strategy, parameters)
        
        # Use provided symbols or default comprehensive set
        if not symbols:
            analysis_symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'BRK-B', 'UNH', 'JNJ']
        else:
            analysis_symbols = symbols
        
        await update_job_progress(job_id, 40, f"Analyzing {len(analysis_symbols)} symbols: {', '.join(analysis_symbols[:3])}{'...' if len(analysis_symbols) > 3 else ''}")
        
        # Basic analysis (similar to quick analysis but more detailed)
        quick_analysis = await analyze_strategy_quick(strategy_id, user_id, analysis_symbols)
        
        await update_job_progress(job_id, 50, "Calculating advanced metrics")

        # Additional comprehensive metrics
        signal_analysis = {
            "total_signals": len(signals),
            "signal_breakdown": {},
            "recent_signals": []
        }
        
        # Group signals by type
        signal_types = {}
        for signal in signals:
            signal_type = signal.signal_type
            if signal_type not in signal_types:
                signal_types[signal_type] = 0
            signal_types[signal_type] += 1
            
        signal_analysis["signal_breakdown"] = signal_types
        signal_analysis["recent_signals"] = [
            {
                "signal_type": s.signal_type,
                "symbol": s.symbol,
                "signal_strength": float(s.signal_strength),
                "created_at": s.created_at.isoformat()
            } for s in signals[:10]  # Last 10 signals
        ]

        await update_job_progress(job_id, 70, "Analyzing performance history")

        # Performance analysis
        performance_analysis = {
            "total_records": len(performance_records),
            "performance_summary": {},
            "trend_analysis": {}
        }
        
        if performance_records:
            avg_return = sum(float(p.return_percentage or 0) for p in performance_records) / len(performance_records)
            avg_sharpe = sum(float(p.sharpe_ratio or 0) for p in performance_records) / len(performance_records)
            
            performance_analysis["performance_summary"] = {
                "average_return_percentage": avg_return,
                "average_sharpe_ratio": avg_sharpe,
                "total_periods": len(performance_records)
            }

        await update_job_progress(job_id, 90, "Generating comprehensive report")

        # Compile comprehensive results
        comprehensive_result = {
            "strategy_id": strategy_id,
            "analysis_type": "comprehensive", 
            "basic_analysis": _convert_decimals_to_json(quick_analysis),
            "signal_analysis": signal_analysis,
            "performance_analysis": performance_analysis,
            "recommendations": _generate_comprehensive_recommendations(quick_analysis, signal_analysis, performance_analysis),
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
            "detailed_metrics": {
                "strategy_complexity": len(parameters),
                "signal_generation_rate": len(signals) / max(1, 30),  # Simplified for now
                "analysis_completeness": "full"
            }
        }

        await update_job_status(
            job_id, 
            "success", 
            {
                "progress_percent": 100,
                "progress_message": "Comprehensive analysis complete",
                "result": comprehensive_result
            }
        )

    except Exception as e:
        await update_job_status(
            job_id, 
            "failed", 
            {
                "error": str(e),
                "progress_message": f"Analysis failed: {str(e)}"
            }
        )


def _generate_comprehensive_recommendations(basic_analysis: dict, signal_analysis: dict, performance_analysis: dict) -> List[str]:
    """Generate comprehensive recommendations based on all analysis data"""
    recommendations = []
    
    # Signal-based recommendations
    total_signals = signal_analysis.get("total_signals", 0)
    if total_signals == 0:
        recommendations.append("Strategy has not generated any signals yet - consider running with market data")
    elif total_signals < 10:
        recommendations.append("Limited signal history - monitor strategy performance over longer periods")
    
    # Performance-based recommendations  
    perf_summary = performance_analysis.get("performance_summary", {})
    avg_return = perf_summary.get("average_return_percentage", 0)
    
    if avg_return > 10:
        recommendations.append("Strategy shows strong historical performance - consider increasing position sizes")
    elif avg_return < 0:
        recommendations.append("Strategy showing negative returns - review parameters and risk management")
    
    # Risk-based recommendations from basic analysis
    risk_metrics = basic_analysis.get("risk_metrics", {})
    risk_score = float(risk_metrics.get("risk_score", 0))
    
    if risk_score > 0.7:
        recommendations.append("High risk score detected - consider reducing position sizes or adjusting parameters")
    elif risk_score < 0.3:
        recommendations.append("Conservative risk profile - may benefit from slight parameter optimization for higher returns")
    
    # Default recommendation
    if not recommendations:
        recommendations.append("Strategy analysis complete - continue monitoring performance and adjust as needed")
    
    return recommendations


def _convert_decimals_to_json(obj):
    """Convert Decimal objects to float for JSON serialization"""
    if isinstance(obj, dict):
        return {k: _convert_decimals_to_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_decimals_to_json(item) for item in obj]
    elif isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    else:
        return obj