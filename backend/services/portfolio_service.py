# services/portfolio_service.py - Modern async portfolio service
"""
Service layer for portfolio operations and management.
Handles portfolio CRUD operations, analysis, and trade simulation.
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Dict, Optional, Any
import asyncio

from sqlmodel import select
from sqlalchemy import and_, desc

from core.db import get_async_session_context
from core.logger import get_logger
from core.portfolio_engine import PortfolioEngine
from models.db_models import Portfolio, Position, Transaction, WorkspaceMembership
from services.job_service import create_job, update_job_status, update_job_progress

logger = get_logger(__name__)

# ===============================
# Basic Portfolio CRUD Operations
# ===============================

async def create_portfolio(
    user_id: int,
    workspace_id: int,
    name: str,
    description: str = "",
    initial_cash: Decimal = Decimal('10000.00')
) -> Portfolio:
    """
    Create a new portfolio for a user in a workspace.
    """
    logger.info(f"Creating portfolio '{name}' for user {user_id} in workspace {workspace_id}")

    async with get_async_session_context() as session:
        # Verify workspace membership
        membership_result = await session.exec(
            select(WorkspaceMembership).where(
                and_(
                    WorkspaceMembership.workspace_id == workspace_id,
                    WorkspaceMembership.user_profile_id == user_id
                )
            )
        )
        if not membership_result.first():
            raise ValueError(f"User {user_id} does not have access to workspace {workspace_id}")

        # Check if portfolio name already exists in this workspace
        existing_result = await session.exec(
            select(Portfolio).where(
                and_(
                    Portfolio.workspace_id == workspace_id,
                    Portfolio.name == name
                )
            )
        )
        if existing_result.first():
            raise ValueError(f"Portfolio '{name}' already exists in this workspace")

        # Create new portfolio
        portfolio = Portfolio(
            created_by=user_id,
            workspace_id=workspace_id,
            name=name,
            description=description,
            initial_cash=initial_cash,
            current_cash=initial_cash,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        session.add(portfolio)
        await session.commit()
        await session.refresh(portfolio)

        logger.info(f"Created portfolio '{name}' with ID {portfolio.id}")
        return portfolio

async def get_portfolio(portfolio_id: int, user_id: int) -> Portfolio:
    """
    Get portfolio by ID with access validation.
    """
    async with get_async_session_context() as session:
        # Get portfolio with workspace membership check
        result = await session.exec(
            select(Portfolio)
            .join(WorkspaceMembership, Portfolio.workspace_id == WorkspaceMembership.workspace_id)
            .where(
                and_(
                    Portfolio.id == portfolio_id,
                    WorkspaceMembership.user_profile_id == user_id
                )
            )
        )
        portfolio = result.first()

        if not portfolio:
            raise ValueError(f"Portfolio {portfolio_id} not found or access denied")

        return portfolio

async def update_portfolio(
    portfolio_id: int,
    user_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    is_active: Optional[bool] = None
) -> Portfolio:
    """
    Update portfolio details with access validation.
    """
    async with get_async_session_context() as session:
        # First verify access to portfolio
        portfolio = await get_portfolio(portfolio_id, user_id)
        
        # Update fields if provided
        if name is not None:
            portfolio.name = name
        if description is not None:
            portfolio.description = description
        if is_active is not None:
            portfolio.is_active = is_active
            
        # Update timestamp
        portfolio.updated_at = datetime.now(timezone.utc)
        
        session.add(portfolio)
        await session.commit()
        await session.refresh(portfolio)
        
        logger.info(f"Updated portfolio {portfolio_id} for user {user_id}")
        return portfolio

async def get_user_portfolios(user_id: int, workspace_id: Optional[int] = None) -> List[Portfolio]:
    """
    Get all portfolios for a user, optionally filtered by workspace.
    """
    async with get_async_session_context() as session:
        query = (
            select(Portfolio)
            .join(WorkspaceMembership, Portfolio.workspace_id == WorkspaceMembership.workspace_id)
            .where(WorkspaceMembership.user_profile_id == user_id)
        )

        if workspace_id:
            query = query.where(Portfolio.workspace_id == workspace_id)

        query = query.order_by(desc(Portfolio.created_at))

        result = await session.exec(query)
        return result.all()

async def get_portfolio_positions(portfolio_id: int, user_id: int) -> List[Position]:
    """
    Get all positions for a portfolio with access validation.
    """
    # First verify access to portfolio
    await get_portfolio(portfolio_id, user_id)

    async with get_async_session_context() as session:
        result = await session.exec(
            select(Position).where(Position.portfolio_id == portfolio_id)
        )
        return result.all()

async def get_portfolio_transactions(
    portfolio_id: int, 
    user_id: int,
    limit: int = 50,
    offset: int = 0
) -> List[Transaction]:
    """
    Get transaction history for a portfolio with access validation.
    """
    # First verify access to portfolio
    await get_portfolio(portfolio_id, user_id)

    async with get_async_session_context() as session:
        result = await session.exec(
            select(Transaction)
            .where(Transaction.portfolio_id == portfolio_id)
            .order_by(desc(Transaction.executed_at))
            .limit(limit)
            .offset(offset)
        )
        return result.all()

# ===============================
# Portfolio Analysis Operations
# ===============================

async def analyze_portfolio_quick(portfolio_id: int, user_id: int) -> Dict[str, Any]:
    """
    Quick portfolio analysis (synchronous).
    """
    logger.info(f"Running quick analysis for portfolio {portfolio_id}")

    try:
        # Get portfolio and positions
        portfolio = await get_portfolio(portfolio_id, user_id)
        positions = await get_portfolio_positions(portfolio_id, user_id)

        # Prepare data for engine
        engine = PortfolioEngine()
        cash = portfolio.current_cash
        position_data = []

        for pos in positions:
            if pos.current_price:
                position_data.append({
                    'symbol': pos.symbol,
                    'quantity': pos.quantity,
                    'average_price': pos.average_price,
                    'current_price': pos.current_price
                })

        # Prepare portfolio data for engine
        portfolio_data = {
            'id': portfolio.id,
            'initial_cash': portfolio.initial_cash,
            'current_cash': portfolio.current_cash
        }
        
        # Prepare current prices (for now, use the stored current_price)
        current_prices = {}
        for pos in position_data:
            if 'current_price' in pos:
                current_prices[pos['symbol']] = pos['current_price']
        
        # Run analysis
        analysis = engine.analyze_portfolio(portfolio_data, position_data, current_prices)

        # Convert Decimal values to float for JSON serialization
        def convert_decimals(obj):
            if isinstance(obj, dict):
                return {k: convert_decimals(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_decimals(item) for item in obj]
            elif isinstance(obj, Decimal):
                return float(obj)
            else:
                return obj

        return convert_decimals(analysis)

    except Exception as e:
        logger.error(f"Error in quick portfolio analysis: {e}")
        raise

async def analyze_portfolio_comprehensive(
    portfolio_id: int, 
    user_id: int, 
    workspace_id: int
) -> str:
    """
    Comprehensive portfolio analysis (asynchronous job).
    Returns job_id for tracking progress.
    """
    logger.info(f"Starting comprehensive analysis job for portfolio {portfolio_id}")

    # Create job
    job = await create_job(
        user_id=user_id,
        job_type="portfolio_analysis_comprehensive",
        workspace_id=workspace_id,
        priority="normal",
        metadata={
            "portfolio_id": portfolio_id,
            "analysis_type": "comprehensive"
        },
        estimated_duration=120  # 2 minutes estimate
    )

    # Start async processing
    asyncio.create_task(_process_comprehensive_analysis(job.job_id, portfolio_id, user_id))

    return job.job_id

async def _process_comprehensive_analysis(job_id: str, portfolio_id: int, user_id: int):
    """
    Background task for comprehensive portfolio analysis.
    """
    try:
        await update_job_status(job_id, "running")
        await update_job_progress(job_id, 10, "Fetching portfolio data")

        # Get portfolio data
        portfolio = await get_portfolio(portfolio_id, user_id)
        positions = await get_portfolio_positions(portfolio_id, user_id)
        transactions = await get_portfolio_transactions(portfolio_id, user_id, limit=1000)

        await update_job_progress(job_id, 30, "Running basic analysis")

        # Run comprehensive analysis
        engine = PortfolioEngine()
        cash = portfolio.current_cash
        position_data = []

        for pos in positions:
            if pos.current_price:
                position_data.append({
                    'symbol': pos.symbol,
                    'quantity': pos.quantity,
                    'average_price': pos.average_price,
                    'current_price': pos.current_price
                })

        # Prepare portfolio data for engine
        portfolio_data = {
            'id': portfolio.id,
            'initial_cash': portfolio.initial_cash,
            'current_cash': portfolio.current_cash
        }
        
        # Prepare current prices (for now, use the stored current_price)
        current_prices = {}
        for pos in position_data:
            if 'current_price' in pos:
                current_prices[pos['symbol']] = pos['current_price']
        
        # Basic analysis
        analysis = engine.analyze_portfolio(portfolio_data, position_data, current_prices)
        await update_job_progress(job_id, 50, "Calculating risk metrics")

        # Risk validation
        validation = engine.validate_portfolio_state(cash, position_data)
        await update_job_progress(job_id, 70, "Analyzing transaction history")

        # Transaction analysis
        transaction_analysis = _analyze_transaction_history(transactions)
        await update_job_progress(job_id, 90, "Generating report")

        # Compile comprehensive results
        def convert_decimals(obj):
            if isinstance(obj, dict):
                return {k: convert_decimals(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_decimals(item) for item in obj]
            elif isinstance(obj, Decimal):
                return float(obj)
            elif isinstance(obj, datetime):
                return obj.isoformat()
            else:
                return obj

        comprehensive_result = {
            'portfolio_analysis': convert_decimals(analysis),
            'risk_validation': convert_decimals(validation),
            'transaction_analysis': convert_decimals(transaction_analysis),
            'recommendations': _generate_recommendations(analysis, validation),
            'analysis_timestamp': datetime.now(timezone.utc).isoformat()
        }

        await update_job_status(
            job_id, 
            "success", 
            {
                'progress_percent': 100,
                'progress_message': 'Analysis complete',
                'result': comprehensive_result
            }
        )

        logger.info(f"Comprehensive analysis completed for portfolio {portfolio_id}")

    except Exception as e:
        logger.error(f"Error in comprehensive analysis: {e}")
        await update_job_status(
            job_id, 
            "failed", 
            {
                'error': str(e),
                'progress_message': f'Analysis failed: {str(e)}'
            }
        )

def _analyze_transaction_history(transactions: List[Transaction]) -> Dict[str, Any]:
    """
    Analyze transaction patterns and statistics.
    """
    if not transactions:
        return {'total_transactions': 0, 'patterns': {}}

    # Basic transaction stats
    total_trades = len(transactions)
    buy_trades = sum(1 for t in transactions if t.transaction_type == 'buy')
    sell_trades = sum(1 for t in transactions if t.transaction_type == 'sell')
    
    total_volume = sum(float(t.total_amount) for t in transactions)
    
    # Symbol frequency
    symbol_counts = {}
    for t in transactions:
        symbol_counts[t.symbol] = symbol_counts.get(t.symbol, 0) + 1
    
    most_traded = max(symbol_counts.items(), key=lambda x: x[1]) if symbol_counts else None

    return {
        'total_transactions': total_trades,
        'buy_trades': buy_trades,
        'sell_trades': sell_trades,
        'total_volume': total_volume,
        'most_traded_symbol': most_traded[0] if most_traded else None,
        'most_traded_count': most_traded[1] if most_traded else 0,
        'unique_symbols': len(symbol_counts)
    }

def _generate_recommendations(analysis: Dict, validation: Dict) -> List[str]:
    """
    Generate portfolio recommendations based on analysis.
    """
    recommendations = []
    
    # Risk-based recommendations
    if validation.get('warnings'):
        for warning in validation['warnings']:
            if 'concentration' in warning.lower():
                recommendations.append("Consider diversifying your portfolio to reduce concentration risk")
    
    # Value-based recommendations
    total_value = analysis.get('total_value', 0)
    if total_value > 0:
        cash_percentage = (analysis.get('cash_balance', 0) / total_value) * 100
        if cash_percentage > 20:
            recommendations.append("You have significant cash reserves - consider investing for better returns")
        elif cash_percentage < 5:
            recommendations.append("Consider maintaining more cash for liquidity and opportunities")
    
    # Default recommendation if none generated
    if not recommendations:
        recommendations.append("Your portfolio appears well-balanced. Continue monitoring regularly.")
    
    return recommendations

# ===============================
# Trade Simulation & Execution
# ===============================

async def simulate_trade(
    portfolio_id: int,
    user_id: int,
    symbol: str,
    quantity: Decimal,
    price: Decimal,
    trade_type: str
) -> Dict[str, Any]:
    """
    Simulate a trade without executing it.
    """
    logger.info(f"Simulating {trade_type} trade: {quantity} shares of {symbol} at ${price}")

    try:
        # Get portfolio data
        portfolio = await get_portfolio(portfolio_id, user_id)
        positions = await get_portfolio_positions(portfolio_id, user_id)

        # Prepare data for simulation
        engine = PortfolioEngine()
        cash = portfolio.current_cash
        position_data = []

        for pos in positions:
            position_data.append({
                'symbol': pos.symbol,
                'quantity': pos.quantity,
                'average_price': pos.average_price
            })

        # Find current position for the symbol
        current_position = None
        for pos in position_data:
            if pos['symbol'] == symbol:
                current_position = {
                    'quantity': pos['quantity'],
                    'average_price': pos['average_price']
                }
                break
        
        # Run simulation
        simulation = engine.simulate_trade(current_position, quantity, price, trade_type)

        # Add execution validation to simulation result
        execution_result = {
            'can_execute': True,  # Basic validation - trade was simulated successfully
            'error': None,
            'trade_impact': simulation,
            'portfolio_before': {
                'cash': float(cash),
                'positions': position_data
            },
            'portfolio_after': simulation,
            'warnings': []
        }
        
        # Convert Decimal values to float
        def convert_decimals(obj):
            if isinstance(obj, dict):
                return {k: convert_decimals(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_decimals(item) for item in obj]
            elif isinstance(obj, Decimal):
                return float(obj)
            else:
                return obj

        return convert_decimals(execution_result)

    except Exception as e:
        logger.error(f"Error simulating trade: {e}")
        raise

async def execute_trade(
    portfolio_id: int,
    user_id: int,
    symbol: str,
    quantity: Decimal,
    price: Decimal,
    trade_type: str
) -> Transaction:
    """
    Execute a trade and update portfolio.
    """
    logger.info(f"Executing {trade_type} trade: {quantity} shares of {symbol} at ${price}")

    try:
        # First simulate to validate
        simulation = await simulate_trade(portfolio_id, user_id, symbol, quantity, price, trade_type)
        
        if not simulation['can_execute']:
            raise ValueError(f"Trade cannot be executed: {simulation['error']}")

        async with get_async_session_context() as session:
            # Get portfolio
            portfolio = await get_portfolio(portfolio_id, user_id)
            
            # Create transaction record
            transaction = Transaction(
                portfolio_id=portfolio_id,
                symbol=symbol,
                quantity=quantity,
                price=price,
                transaction_type=trade_type,
                total_amount=quantity * price,
                created_by=user_id,
                executed_at=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc)
            )
            session.add(transaction)

            # Update or create position
            position_result = await session.exec(
                select(Position).where(
                    and_(
                        Position.portfolio_id == portfolio_id,
                        Position.symbol == symbol
                    )
                )
            )
            position = position_result.first()

            if trade_type == 'buy':
                if position:
                    # Update existing position
                    new_quantity = position.quantity + quantity
                    new_avg_price = ((position.quantity * position.average_price) + 
                                   (quantity * price)) / new_quantity
                    position.quantity = new_quantity
                    position.average_price = new_avg_price
                    position.updated_at = datetime.now(timezone.utc)
                else:
                    # Create new position
                    position = Position(
                        portfolio_id=portfolio_id,
                        symbol=symbol,
                        quantity=quantity,
                        average_price=price,
                        current_price=price,
                        updated_at=datetime.now(timezone.utc)
                    )
                    session.add(position)

                # Update portfolio cash
                portfolio.current_cash -= quantity * price

            elif trade_type == 'sell':
                if position:
                    position.quantity -= quantity
                    position.updated_at = datetime.now(timezone.utc)
                    if position.quantity <= 0:
                        await session.delete(position)

                # Update portfolio cash
                portfolio.current_cash += quantity * price

            # Update portfolio timestamp
            portfolio.updated_at = datetime.now(timezone.utc)
            session.add(portfolio)

            await session.commit()
            await session.refresh(transaction)

            logger.info(f"Trade executed successfully: {transaction.id}")
            return transaction

    except Exception as e:
        logger.error(f"Error executing trade: {e}")
        raise

# ===============================
# Portfolio Validation
# ===============================

async def validate_portfolio_state(portfolio_id: int, user_id: int) -> Dict[str, Any]:
    """
    Validate portfolio state and check for issues.
    """
    try:
        # Get portfolio data
        portfolio = await get_portfolio(portfolio_id, user_id)
        positions = await get_portfolio_positions(portfolio_id, user_id)

        # Prepare data for validation
        engine = PortfolioEngine()
        cash = portfolio.current_cash
        position_data = []

        for pos in positions:
            if pos.current_price:
                position_data.append({
                    'symbol': pos.symbol,
                    'quantity': pos.quantity,
                    'average_price': pos.average_price,
                    'current_price': pos.current_price
                })

        # Run validation
        validation = engine.validate_portfolio_state(cash, position_data)
        
        return validation

    except Exception as e:
        logger.error(f"Error validating portfolio: {e}")
        raise