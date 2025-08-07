# api/portfolio.py - Portfolio API endpoints following design rulebook
from fastapi import APIRouter, HTTPException, Depends, Path, Query
from typing import Optional
from decimal import Decimal
from datetime import datetime

from models.db_models import UserProfile
from models.portfolio_models import (
    PortfolioCreateRequest, PortfolioUpdateRequest, PortfolioResponse,
    PortfolioListResponse, PositionResponse, PositionListResponse,
    TransactionResponse, TransactionListResponse,
    TradeSimulationRequest, TradeExecutionRequest,
    TradeSimulationResponse, TradeExecutionResponse,
    PortfolioAnalysisRequest, PortfolioAnalysisResponse,
    PortfolioValidationResponse
)
from core.security import get_current_user
from core.logger import get_logger
from core.plugin import apply_sorting, apply_pagination, get_pagination_params, get_sorting_params
from services.portfolio_service import (
    create_portfolio, get_portfolio, get_user_portfolios, update_portfolio,
    get_portfolio_positions, get_portfolio_transactions,
    analyze_portfolio_quick, analyze_portfolio_comprehensive,
    simulate_trade, execute_trade, validate_portfolio_state
)

logger = get_logger(__name__)
router = APIRouter()

# ===== WORKSPACE-SCOPED PORTFOLIO COLLECTION =====
# Following Pattern 1: Workspace-Scoped Resources

@router.get("/workspace/{workspace_id}/portfolios")
async def list_workspace_portfolios(
    workspace_id: int = Path(...),
    current_user: UserProfile = Depends(get_current_user),
    # Standard pagination/sorting
    pagination: dict = Depends(get_pagination_params),
    sorting: dict = Depends(get_sorting_params)
):
    """
    List portfolios in a workspace with filtering, sorting, and pagination.
    Following Pattern 1: Workspace-Scoped Resources
    """
    try:
        # Get all portfolios for user in workspace
        all_portfolios = await get_user_portfolios(
            user_id=current_user.id,
            workspace_id=workspace_id
        )
        
        # Apply sorting/pagination in API layer
        sorted_portfolios = apply_sorting(all_portfolios, sorting["sort"], sorting["order"])
        result = apply_pagination(sorted_portfolios, pagination["page"], pagination["limit"])
        
        # Convert to response format
        portfolio_responses = []
        for portfolio in result["data"]:
            # Get position count for summary
            positions = await get_portfolio_positions(portfolio.id, current_user.id)
            
            portfolio_response = PortfolioResponse(
                id=portfolio.id,
                name=portfolio.name,
                description=portfolio.description,
                created_by=portfolio.created_by,
                workspace_id=portfolio.workspace_id,
                initial_cash=portfolio.initial_cash,
                current_cash=portfolio.current_cash,
                is_active=portfolio.is_active,
                created_at=portfolio.created_at,
                updated_at=portfolio.updated_at,
                position_count=len(positions)
            )
            portfolio_responses.append(portfolio_response)
        
        return PortfolioListResponse(
            portfolios=portfolio_responses,
            total_count=result["pagination"]["total"],
            page=result["pagination"]["page"],
            page_size=result["pagination"]["limit"]
        )
        
    except Exception as e:
        logger.error(f"Error listing portfolios for workspace {workspace_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve portfolios")

@router.post("/workspace/{workspace_id}/portfolios", status_code=201)
async def create_workspace_portfolio(
    request: PortfolioCreateRequest,
    workspace_id: int = Path(...),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Create a new portfolio in the specified workspace.
    Following Pattern 1: Workspace-Scoped Resources
    """
    logger.info(f"Creating portfolio '{request.name}' for user {current_user.id} in workspace {workspace_id}")
    
    try:
        portfolio = await create_portfolio(
            user_id=current_user.id,
            workspace_id=workspace_id,
            name=request.name,
            description=request.description,
            initial_cash=request.initial_cash
        )
        
        response = PortfolioResponse(
            id=portfolio.id,
            name=portfolio.name,
            description=portfolio.description,
            created_by=portfolio.created_by,
            workspace_id=portfolio.workspace_id,
            initial_cash=portfolio.initial_cash,
            current_cash=portfolio.current_cash,
            is_active=portfolio.is_active,
            created_at=portfolio.created_at,
            updated_at=portfolio.updated_at,
            position_count=0
        )
        
        logger.info(f"Created portfolio {portfolio.id}")
        return response
        
    except ValueError as e:
        logger.error(f"Failed to create portfolio: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error creating portfolio: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create portfolio")

# ===== SINGLE PORTFOLIO OPERATIONS =====

@router.get("/workspace/{workspace_id}/portfolios/{portfolio_id}")
async def get_workspace_portfolio(
    workspace_id: int = Path(...),
    portfolio_id: int = Path(...),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get portfolio details by ID within a workspace.
    Following Pattern 1: Workspace-Scoped Resources
    """
    try:
        portfolio = await get_portfolio(portfolio_id, current_user.id)
        
        # Verify portfolio belongs to the specified workspace
        if portfolio.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Portfolio not found in specified workspace")
        
        # Get additional details
        positions = await get_portfolio_positions(portfolio_id, current_user.id)
        
        return PortfolioResponse(
            id=portfolio.id,
            name=portfolio.name,
            description=portfolio.description,
            created_by=portfolio.created_by,
            workspace_id=portfolio.workspace_id,
            initial_cash=portfolio.initial_cash,
            current_cash=portfolio.current_cash,
            is_active=portfolio.is_active,
            created_at=portfolio.created_at,
            updated_at=portfolio.updated_at,
            position_count=len(positions)
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting portfolio {portfolio_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve portfolio")

@router.patch("/workspace/{workspace_id}/portfolios/{portfolio_id}")
async def update_workspace_portfolio(
    request: PortfolioUpdateRequest,
    workspace_id: int = Path(...),
    portfolio_id: int = Path(...),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Update portfolio details.
    Following Pattern 1: Workspace-Scoped Resources
    """
    try:
        # Verify portfolio exists and belongs to workspace
        existing_portfolio = await get_portfolio(portfolio_id, current_user.id)
        if existing_portfolio.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Portfolio not found in specified workspace")
        
        # Update portfolio using service layer
        updated_portfolio = await update_portfolio(
            portfolio_id=portfolio_id,
            user_id=current_user.id,
            name=request.name,
            description=request.description
        )
        
        # Get position count for response
        positions = await get_portfolio_positions(portfolio_id, current_user.id)
        
        return PortfolioResponse(
            id=updated_portfolio.id,
            name=updated_portfolio.name,
            description=updated_portfolio.description,
            created_by=updated_portfolio.created_by,
            workspace_id=updated_portfolio.workspace_id,
            initial_cash=updated_portfolio.initial_cash,
            current_cash=updated_portfolio.current_cash,
            is_active=updated_portfolio.is_active,
            created_at=updated_portfolio.created_at,
            updated_at=updated_portfolio.updated_at,
            position_count=len(positions)
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating portfolio {portfolio_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update portfolio")

# ===== PORTFOLIO POSITIONS =====

@router.get("/workspace/{workspace_id}/portfolios/{portfolio_id}/positions")
async def get_portfolio_positions_api(
    workspace_id: int = Path(...),
    portfolio_id: int = Path(...),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get all positions for a portfolio.
    Following Pattern 1: Workspace-Scoped Resources
    """
    try:
        # Verify portfolio belongs to workspace
        portfolio = await get_portfolio(portfolio_id, current_user.id)
        if portfolio.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Portfolio not found in specified workspace")
        
        positions = await get_portfolio_positions(portfolio_id, current_user.id)
        
        position_responses = []
        for position in positions:
            # Calculate market value and P&L
            market_value = None
            unrealized_pnl = None
            unrealized_pnl_percentage = None
            
            if position.current_price:
                market_value = position.quantity * position.current_price
                cost_basis = position.quantity * position.average_price
                unrealized_pnl = market_value - cost_basis
                if cost_basis > 0:
                    unrealized_pnl_percentage = (unrealized_pnl / cost_basis) * 100
            
            position_response = PositionResponse(
                id=position.id,
                symbol=position.symbol,
                quantity=position.quantity,
                average_price=position.average_price,
                current_price=position.current_price,
                position_type=position.position_type,
                opened_at=position.opened_at,
                updated_at=position.updated_at,
                market_value=market_value,
                unrealized_pnl=unrealized_pnl,
                unrealized_pnl_percentage=unrealized_pnl_percentage
            )
            position_responses.append(position_response)
        
        return PositionListResponse(
            positions=position_responses,
            total_count=len(position_responses)
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting positions for portfolio {portfolio_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve positions")

# ===== PORTFOLIO TRANSACTIONS =====

@router.get("/workspace/{workspace_id}/portfolios/{portfolio_id}/transactions")
async def get_portfolio_transactions_api(
    workspace_id: int = Path(...),
    portfolio_id: int = Path(...),
    current_user: UserProfile = Depends(get_current_user),
    pagination: dict = Depends(get_pagination_params)
):
    """
    Get transaction history for a portfolio.
    Following Pattern 1: Workspace-Scoped Resources
    """
    try:
        # Verify portfolio belongs to workspace
        portfolio = await get_portfolio(portfolio_id, current_user.id)
        if portfolio.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Portfolio not found in specified workspace")
        
        # Get transactions with pagination
        limit = pagination["limit"]
        offset = (pagination["page"] - 1) * limit
        
        transactions = await get_portfolio_transactions(
            portfolio_id, current_user.id, limit=limit, offset=offset
        )
        
        # Get total count (this would need to be implemented in service)
        all_transactions = await get_portfolio_transactions(
            portfolio_id, current_user.id, limit=10000, offset=0
        )
        total_count = len(all_transactions)
        
        transaction_responses = []
        for transaction in transactions:
            transaction_response = TransactionResponse(
                id=transaction.id,
                transaction_type=transaction.transaction_type,
                symbol=transaction.symbol,
                quantity=transaction.quantity,
                price=transaction.price,
                total_amount=transaction.total_amount,
                fees=transaction.fees,
                notes=transaction.notes,
                executed_at=transaction.executed_at,
                created_at=transaction.created_at
            )
            transaction_responses.append(transaction_response)
        
        return TransactionListResponse(
            transactions=transaction_responses,
            total_count=total_count,
            page=pagination["page"],
            page_size=pagination["limit"]
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting transactions for portfolio {portfolio_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve transactions")

# ===== TRADE OPERATIONS =====

@router.post("/workspace/{workspace_id}/portfolios/{portfolio_id}/trades/simulate")
async def simulate_portfolio_trade(
    request: TradeSimulationRequest,
    workspace_id: int = Path(...),
    portfolio_id: int = Path(...),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Simulate a trade without executing it.
    Following Pattern 3: Resource Actions
    """
    try:
        # Verify portfolio belongs to workspace
        portfolio = await get_portfolio(portfolio_id, current_user.id)
        if portfolio.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Portfolio not found in specified workspace")
        
        simulation = await simulate_trade(
            portfolio_id=portfolio_id,
            user_id=current_user.id,
            symbol=request.symbol,
            quantity=request.quantity,
            price=request.price,
            trade_type=request.trade_type
        )
        
        return TradeSimulationResponse(
            can_execute=simulation.get('can_execute', False),
            error=simulation.get('error'),
            trade_impact=simulation.get('trade_impact'),
            portfolio_before=simulation.get('portfolio_before'),
            portfolio_after=simulation.get('portfolio_after'),
            warnings=simulation.get('warnings', [])
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error simulating trade for portfolio {portfolio_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to simulate trade")

@router.post("/workspace/{workspace_id}/portfolios/{portfolio_id}/trades/execute")
async def execute_portfolio_trade(
    request: TradeExecutionRequest,
    workspace_id: int = Path(...),
    portfolio_id: int = Path(...),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Execute a trade in the portfolio.
    Following Pattern 3: Resource Actions
    """
    logger.info(f"Executing {request.trade_type} trade: {request.quantity} shares of {request.symbol} at ${request.price}")
    
    try:
        # Verify portfolio belongs to workspace
        portfolio = await get_portfolio(portfolio_id, current_user.id)
        if portfolio.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Portfolio not found in specified workspace")
        
        transaction = await execute_trade(
            portfolio_id=portfolio_id,
            user_id=current_user.id,
            symbol=request.symbol,
            quantity=request.quantity,
            price=request.price,
            trade_type=request.trade_type
        )
        
        # Get updated portfolio to return current cash
        updated_portfolio = await get_portfolio(portfolio_id, current_user.id)
        
        return TradeExecutionResponse(
            transaction_id=transaction.id,
            trade_type=transaction.transaction_type,
            symbol=transaction.symbol,
            quantity=transaction.quantity,
            price=transaction.price,
            total_amount=transaction.total_amount,
            fees=transaction.fees,
            executed_at=transaction.executed_at,
            portfolio_cash=updated_portfolio.current_cash,
            position_created=True,  # This would need logic to determine
            position_updated=False,
            position_closed=False
        )
        
    except ValueError as e:
        logger.error(f"Failed to execute trade: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error executing trade: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to execute trade")

# ===== PORTFOLIO ANALYSIS =====

@router.post("/workspace/{workspace_id}/portfolios/{portfolio_id}/analyze")
async def analyze_portfolio(
    request: PortfolioAnalysisRequest,
    workspace_id: int = Path(...),
    portfolio_id: int = Path(...),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Analyze portfolio performance and risk metrics.
    Following Pattern 3: Resource Actions
    """
    try:
        # Verify portfolio belongs to workspace
        portfolio = await get_portfolio(portfolio_id, current_user.id)
        if portfolio.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Portfolio not found in specified workspace")
        
        if request.analysis_type == "quick":
            # Quick synchronous analysis
            analysis = await analyze_portfolio_quick(portfolio_id, current_user.id)
            
            return PortfolioAnalysisResponse(
                portfolio_id=portfolio_id,
                analysis_type="quick",
                analysis_timestamp=analysis.get('analysis_timestamp'),
                total_value=analysis.get('total_value', 0),
                cash_balance=analysis.get('cash_balance', 0),
                positions_value=analysis.get('positions_value', 0),
                total_return=analysis.get('total_return'),
                return_percentage=analysis.get('return_percentage'),
                allocation=analysis.get('allocation'),
                risk_metrics=analysis.get('risk_metrics'),
                positions=analysis.get('positions')
            )
            
        elif request.analysis_type == "comprehensive":
            # Long-running job-based analysis
            job_id = await analyze_portfolio_comprehensive(
                portfolio_id, current_user.id, workspace_id
            )
            
            return PortfolioAnalysisResponse(
                portfolio_id=portfolio_id,
                analysis_type="comprehensive",
                analysis_timestamp=datetime.now(),
                total_value=Decimal('0'),
                cash_balance=Decimal('0'),
                positions_value=Decimal('0'),
                job_id=job_id
            )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing portfolio {portfolio_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to analyze portfolio")

@router.get("/workspace/{workspace_id}/portfolios/{portfolio_id}/validate")
async def validate_portfolio(
    workspace_id: int = Path(...),
    portfolio_id: int = Path(...),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Validate portfolio state and check for issues.
    Following Pattern 3: Resource Actions
    """
    try:
        # Verify portfolio belongs to workspace
        portfolio = await get_portfolio(portfolio_id, current_user.id)
        if portfolio.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Portfolio not found in specified workspace")
        
        validation = await validate_portfolio_state(portfolio_id, current_user.id)
        
        return PortfolioValidationResponse(
            portfolio_id=portfolio_id,
            is_valid=validation.get('is_valid', False),
            issues=validation.get('issues', []),
            warnings=validation.get('warnings', []),
            validation_timestamp=datetime.now()
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating portfolio {portfolio_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to validate portfolio")

# ===== LEGACY ENDPOINTS (for backward compatibility) =====

@router.get("/portfolios")
async def list_all_user_portfolios_legacy(
    current_user: UserProfile = Depends(get_current_user),
    workspace_id: Optional[int] = Query(None, description="Filter by workspace ID"),
    pagination: dict = Depends(get_pagination_params),
    sorting: dict = Depends(get_sorting_params)
):
    """
    LEGACY: List all portfolios for the current user across workspaces.
    DEPRECATED: Use /workspace/{workspace_id}/portfolios instead.
    """
    try:
        # Get all portfolios for user (across all workspaces they have access to)
        all_portfolios = await get_user_portfolios(
            user_id=current_user.id,
            workspace_id=workspace_id
        )
        
        # Apply sorting/pagination in API layer
        sorted_portfolios = apply_sorting(all_portfolios, sorting["sort"], sorting["order"])
        result = apply_pagination(sorted_portfolios, pagination["page"], pagination["limit"])
        
        # Convert to response format
        portfolio_responses = []
        for portfolio in result["data"]:
            positions = await get_portfolio_positions(portfolio.id, current_user.id)
            
            portfolio_response = PortfolioResponse(
                id=portfolio.id,
                name=portfolio.name,
                description=portfolio.description,
                created_by=portfolio.created_by,
                workspace_id=portfolio.workspace_id,
                initial_cash=portfolio.initial_cash,
                current_cash=portfolio.current_cash,
                is_active=portfolio.is_active,
                created_at=portfolio.created_at,
                updated_at=portfolio.updated_at,
                position_count=len(positions)
            )
            portfolio_responses.append(portfolio_response)
        
        return PortfolioListResponse(
            portfolios=portfolio_responses,
            total_count=result["pagination"]["total"],
            page=result["pagination"]["page"],
            page_size=result["pagination"]["limit"]
        )
        
    except Exception as e:
        logger.error(f"Error listing portfolios for user {current_user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve portfolios")