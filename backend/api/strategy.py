# api/strategy.py
"""
Strategy API endpoints - workspace-scoped REST API for trading strategy management
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, Path
from fastapi.responses import JSONResponse

from core.plugin import get_pagination_params, get_sorting_params, apply_sorting, apply_pagination
from core.security import get_current_user
from models.db_models import UserProfile
from models.strategy_models import (
    StrategyCreateRequest, StrategyUpdateRequest, ParameterUpdateRequest,
    AnalysisRequest, BacktestRequest, SignalGenerationRequest, CloneStrategyRequest,
    StrategyResponse, StrategyListResponse, StrategyParameterResponse,
    SignalListResponse, PerformanceListResponse, QuickAnalysisResponse,
    ComprehensiveAnalysisResponse, BacktestResponse, ValidationResponse,
    PublicStrategyListResponse
)
from typing import List, Optional
from services.strategy_service import (
    create_strategy, get_strategy, get_user_strategies, update_strategy,
    get_strategy_parameters, update_strategy_parameter, analyze_strategy_quick,
    analyze_strategy_comprehensive, backtest_strategy, generate_strategy_signals,
    get_strategy_signals, get_strategy_performance, validate_strategy_config,
    clone_strategy, get_public_strategies
)

router = APIRouter()

# ===== WORKSPACE-SCOPED STRATEGY OPERATIONS =====

@router.get("/workspace/{workspace_id}/strategies", response_model=StrategyListResponse)
async def list_strategies(
    workspace_id: int = Path(..., description="Workspace ID"),
    strategy_type: Optional[str] = Query(None, description="Filter by strategy type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    sort: Optional[str] = Query(None, description="Sort field"),
    order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: UserProfile = Depends(get_current_user)
):
    """List strategies in a workspace with filtering, sorting, and pagination"""
    try:
        # Get strategies
        strategies = await get_user_strategies(
            user_id=current_user.id,
            workspace_id=workspace_id,
            strategy_type=strategy_type,
            is_active=is_active
        )
        
        # Add parameter count for each strategy
        strategy_responses = []
        for strategy in strategies:
            try:
                parameters = await get_strategy_parameters(strategy.id, current_user.id)
                parameter_count = len(parameters)
            except:
                parameter_count = 0
            
            strategy_dict = strategy.model_dump()
            strategy_dict["parameter_count"] = parameter_count
            strategy_responses.append(StrategyResponse(**strategy_dict))
        
        # Apply sorting
        if sort:
            strategy_responses = apply_sorting(strategy_responses, sort, order)
        
        # Apply pagination
        paginated_result = apply_pagination(strategy_responses, page, limit)
        
        return StrategyListResponse(
            strategies=paginated_result["data"],
            total_count=paginated_result["pagination"]["total"],
            page=paginated_result["pagination"]["page"],
            page_size=paginated_result["pagination"]["limit"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list strategies: {str(e)}")


@router.post("/workspace/{workspace_id}/strategies", response_model=StrategyResponse, status_code=201)
async def create_strategy_endpoint(
    workspace_id: int = Path(..., description="Workspace ID"),
    request: StrategyCreateRequest = ...,
    current_user: UserProfile = Depends(get_current_user)
):
    """Create a new strategy in the workspace"""
    try:
        strategy = await create_strategy(
            user_id=current_user.id,
            workspace_id=workspace_id,
            name=request.name,
            strategy_type=request.strategy_type,
            description=request.description,
            strategy_code=request.strategy_code,
            risk_level=request.risk_level,
            is_public=request.is_public,
            parameters=request.parameters
        )
        
        # Add parameter count
        try:
            parameters = await get_strategy_parameters(strategy.id, current_user.id)
            parameter_count = len(parameters)
        except:
            parameter_count = 0
        
        strategy_dict = strategy.model_dump()
        strategy_dict["parameter_count"] = parameter_count
        
        return StrategyResponse(**strategy_dict)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create strategy: {str(e)}")


@router.get("/workspace/{workspace_id}/strategies/{strategy_id}", response_model=StrategyResponse)
async def get_strategy_endpoint(
    workspace_id: int = Path(..., description="Workspace ID"),
    strategy_id: int = Path(..., description="Strategy ID"),
    current_user: UserProfile = Depends(get_current_user)
):
    """Get strategy details"""
    try:
        strategy = await get_strategy(strategy_id, current_user.id)
        
        # Verify workspace
        if strategy.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Strategy not found in specified workspace")
        
        # Add parameter count
        try:
            parameters = await get_strategy_parameters(strategy.id, current_user.id)
            parameter_count = len(parameters)
        except:
            parameter_count = 0
        
        strategy_dict = strategy.model_dump()
        strategy_dict["parameter_count"] = parameter_count
        
        return StrategyResponse(**strategy_dict)
        
    except ValueError:
        raise HTTPException(status_code=404, detail="Strategy not found or access denied")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get strategy: {str(e)}")


@router.patch("/workspace/{workspace_id}/strategies/{strategy_id}", response_model=StrategyResponse)
async def update_strategy_endpoint(
    workspace_id: int = Path(..., description="Workspace ID"),
    strategy_id: int = Path(..., description="Strategy ID"),
    request: StrategyUpdateRequest = ...,
    current_user: UserProfile = Depends(get_current_user)
):
    """Update strategy details"""
    try:
        # Verify strategy exists and belongs to workspace
        existing_strategy = await get_strategy(strategy_id, current_user.id)
        if existing_strategy.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Strategy not found in specified workspace")
        
        strategy = await update_strategy(
            strategy_id=strategy_id,
            user_id=current_user.id,
            name=request.name,
            description=request.description,
            strategy_code=request.strategy_code,
            risk_level=request.risk_level,
            is_active=request.is_active
        )
        
        # Add parameter count
        try:
            parameters = await get_strategy_parameters(strategy.id, current_user.id)
            parameter_count = len(parameters)
        except:
            parameter_count = 0
        
        strategy_dict = strategy.model_dump()
        strategy_dict["parameter_count"] = parameter_count
        
        return StrategyResponse(**strategy_dict)
        
    except ValueError:
        raise HTTPException(status_code=404, detail="Strategy not found or access denied")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update strategy: {str(e)}")


# ===== STRATEGY PARAMETERS =====

@router.get("/workspace/{workspace_id}/strategies/{strategy_id}/parameters", response_model=List[StrategyParameterResponse])
async def get_strategy_parameters_endpoint(
    workspace_id: int = Path(..., description="Workspace ID"),
    strategy_id: int = Path(..., description="Strategy ID"),
    current_user: UserProfile = Depends(get_current_user)
):
    """Get strategy parameters"""
    try:
        # Verify strategy exists and belongs to workspace
        strategy = await get_strategy(strategy_id, current_user.id)
        if strategy.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Strategy not found in specified workspace")
        
        parameters = await get_strategy_parameters(strategy_id, current_user.id)
        return [StrategyParameterResponse.model_validate(param) for param in parameters]
        
    except ValueError:
        raise HTTPException(status_code=404, detail="Strategy not found or access denied")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get parameters: {str(e)}")


@router.patch("/workspace/{workspace_id}/strategies/{strategy_id}/parameters/{parameter_name}", response_model=StrategyParameterResponse)
async def update_parameter_endpoint(
    workspace_id: int = Path(..., description="Workspace ID"),
    strategy_id: int = Path(..., description="Strategy ID"),
    parameter_name: str = Path(..., description="Parameter name"),
    request: ParameterUpdateRequest = ...,
    current_user: UserProfile = Depends(get_current_user)
):
    """Update a strategy parameter value"""
    try:
        # Verify strategy exists and belongs to workspace
        strategy = await get_strategy(strategy_id, current_user.id)
        if strategy.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Strategy not found in specified workspace")
        
        parameter = await update_strategy_parameter(
            strategy_id=strategy_id,
            user_id=current_user.id,
            parameter_name=parameter_name,
            current_value=request.current_value
        )
        
        return StrategyParameterResponse.model_validate(parameter)
        
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update parameter: {str(e)}")


# ===== STRATEGY ANALYSIS =====

@router.post("/workspace/{workspace_id}/strategies/{strategy_id}/analyze", response_model=QuickAnalysisResponse | ComprehensiveAnalysisResponse)
async def analyze_strategy_endpoint(
    workspace_id: int = Path(..., description="Workspace ID"),
    strategy_id: int = Path(..., description="Strategy ID"),
    request: AnalysisRequest = ...,
    current_user: UserProfile = Depends(get_current_user)
):
    """Analyze strategy performance and characteristics using real market data"""
    try:
        # Verify strategy exists and belongs to workspace
        strategy = await get_strategy(strategy_id, current_user.id)
        if strategy.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Strategy not found in specified workspace")
        
        if request.analysis_type == "quick":
            analysis = await analyze_strategy_quick(strategy_id, current_user.id, request.symbols)
            return QuickAnalysisResponse(**analysis)
        
        elif request.analysis_type == "comprehensive":
            job_id = await analyze_strategy_comprehensive(strategy_id, current_user.id, request.symbols)
            return ComprehensiveAnalysisResponse(
                strategy_id=strategy_id,
                analysis_type="comprehensive",
                analysis_timestamp=datetime.now(),
                job_id=job_id
            )
        
    except ValueError:
        raise HTTPException(status_code=404, detail="Strategy not found or access denied")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze strategy: {str(e)}")


@router.post("/workspace/{workspace_id}/strategies/{strategy_id}/backtest", response_model=BacktestResponse)
async def backtest_strategy_endpoint(
    workspace_id: int = Path(..., description="Workspace ID"),
    strategy_id: int = Path(..., description="Strategy ID"),
    request: BacktestRequest = ...,
    current_user: UserProfile = Depends(get_current_user)
):
    """DEPRECATED: Strategy backtesting moved to separate Backtesting Engine"""
    try:
        # Verify strategy exists and belongs to workspace
        strategy = await get_strategy(strategy_id, current_user.id)
        if strategy.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Strategy not found in specified workspace")
        
        # This endpoint is deprecated but kept for API compatibility
        raise HTTPException(
            status_code=501, 
            detail={
                "error": "Backtesting has been moved to a separate Backtesting Engine",
                "message": "Please use the Backtesting Engine API endpoints for backtesting functionality",
                "migration_info": {
                    "old_endpoint": f"/workspace/{workspace_id}/strategies/{strategy_id}/backtest",
                    "new_endpoint": f"/workspace/{workspace_id}/backtests",
                    "documentation": "See Backtesting Engine API documentation"
                }
            }
        )
        
    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(status_code=404, detail="Strategy not found or access denied")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process backtest request: {str(e)}")


# ===== SIGNAL MANAGEMENT =====

@router.post("/workspace/{workspace_id}/strategies/{strategy_id}/signals/generate", response_model=SignalListResponse)
async def generate_signals_endpoint(
    workspace_id: int = Path(..., description="Workspace ID"),
    strategy_id: int = Path(..., description="Strategy ID"),
    request: SignalGenerationRequest = ...,
    current_user: UserProfile = Depends(get_current_user)
):
    """Generate trading signals using the strategy with real market data from DataService"""
    try:
        # Verify strategy exists and belongs to workspace
        strategy = await get_strategy(strategy_id, current_user.id)
        if strategy.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Strategy not found in specified workspace")
        
        signals = await generate_strategy_signals(
            strategy_id=strategy_id,
            user_id=current_user.id,
            symbols=request.symbols,
            lookback_days=request.lookback_days
        )
        
        # Convert signals to response format
        signal_responses = []
        for signal in signals:
            signal_response = {
                "signal_type": signal.get("signal_type", "hold"),
                "symbol": signal.get("symbol", "UNKNOWN"),
                "signal_strength": float(signal.get("signal_strength", 0.5)),
                "price": float(signal.get("price", 0.0)),
                "confidence_score": float(signal.get("confidence_score", 0.5)),
                "created_at": signal.get("created_at", datetime.now()),
                "generator": signal.get("generator", "unknown")
            }
            signal_responses.append(signal_response)
        
        return SignalListResponse(
            signals=signal_responses,
            total_count=len(signals)
        )
        
    except ValueError:
        raise HTTPException(status_code=404, detail="Strategy not found or access denied")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate signals: {str(e)}")


@router.get("/workspace/{workspace_id}/strategies/{strategy_id}/signals", response_model=SignalListResponse)
async def get_signals_endpoint(
    workspace_id: int = Path(..., description="Workspace ID"),
    strategy_id: int = Path(..., description="Strategy ID"),
    signal_type: Optional[str] = Query(None, description="Filter by signal type"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    limit: int = Query(50, ge=1, le=100, description="Number of signals to return"),
    current_user: UserProfile = Depends(get_current_user)
):
    """Get signals generated by the strategy"""
    try:
        # Verify strategy exists and belongs to workspace
        strategy = await get_strategy(strategy_id, current_user.id)
        if strategy.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Strategy not found in specified workspace")
        
        signals = await get_strategy_signals(
            strategy_id=strategy_id,
            user_id=current_user.id,
            limit=limit,
            signal_type=signal_type,
            symbol=symbol
        )
        
        return SignalListResponse(
            signals=[signal for signal in signals],  # Signals already in correct format
            total_count=len(signals)
        )
        
    except ValueError:
        raise HTTPException(status_code=404, detail="Strategy not found or access denied")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get signals: {str(e)}")


# ===== PERFORMANCE TRACKING =====

@router.get("/workspace/{workspace_id}/strategies/{strategy_id}/performance", response_model=PerformanceListResponse)
async def get_performance_endpoint(
    workspace_id: int = Path(..., description="Workspace ID"),
    strategy_id: int = Path(..., description="Strategy ID"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    current_user: UserProfile = Depends(get_current_user)
):
    """Get strategy performance records"""
    try:
        # Verify strategy exists and belongs to workspace
        strategy = await get_strategy(strategy_id, current_user.id)
        if strategy.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Strategy not found in specified workspace")
        
        performance_records = await get_strategy_performance(
            strategy_id=strategy_id,
            user_id=current_user.id,
            start_date=start_date,
            end_date=end_date
        )
        
        return PerformanceListResponse(
            performance_records=[record for record in performance_records],  # Records already in correct format  
            total_count=len(performance_records)
        )
        
    except ValueError:
        raise HTTPException(status_code=404, detail="Strategy not found or access denied")  
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get performance: {str(e)}")


# ===== STRATEGY VALIDATION =====

@router.get("/workspace/{workspace_id}/strategies/{strategy_id}/validate", response_model=ValidationResponse)
async def validate_strategy_endpoint(
    workspace_id: int = Path(..., description="Workspace ID"),
    strategy_id: int = Path(..., description="Strategy ID"),
    current_user: UserProfile = Depends(get_current_user)
):
    """Validate strategy configuration and parameters"""
    try:
        # Verify strategy exists and belongs to workspace
        strategy = await get_strategy(strategy_id, current_user.id)
        if strategy.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Strategy not found in specified workspace")
        
        validation = await validate_strategy_config(strategy_id, current_user.id)
        
        return ValidationResponse(
            strategy_id=strategy_id,
            is_valid=validation["is_valid"],
            issues=validation["issues"],
            warnings=validation["warnings"],
            validation_timestamp=validation["validation_timestamp"]
        )
        
    except ValueError:
        raise HTTPException(status_code=404, detail="Strategy not found or access denied")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to validate strategy: {str(e)}")


# ===== STRATEGY CLONING =====

@router.post("/workspace/{workspace_id}/strategies/{strategy_id}/clone", response_model=StrategyResponse, status_code=201)
async def clone_strategy_endpoint(
    workspace_id: int = Path(..., description="Workspace ID"),
    strategy_id: int = Path(..., description="Strategy ID"),
    request: CloneStrategyRequest = ...,
    current_user: UserProfile = Depends(get_current_user)
):
    """Clone an existing strategy"""
    try:
        # Verify strategy exists and belongs to workspace
        strategy = await get_strategy(strategy_id, current_user.id)
        if strategy.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Strategy not found in specified workspace")
        
        cloned_strategy = await clone_strategy(
            strategy_id=strategy_id,
            user_id=current_user.id,
            new_name=request.new_name,
            target_workspace_id=request.target_workspace_id or workspace_id
        )
        
        # Add parameter count
        try:
            parameters = await get_strategy_parameters(cloned_strategy.id, current_user.id)
            parameter_count = len(parameters)
        except:
            parameter_count = 0
        
        strategy_dict = cloned_strategy.model_dump()
        strategy_dict["parameter_count"] = parameter_count
        
        return StrategyResponse(**strategy_dict)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clone strategy: {str(e)}")


# ===== PUBLIC STRATEGIES =====

@router.get("/strategies/public", response_model=PublicStrategyListResponse)
async def get_public_strategies_endpoint(
    strategy_type: Optional[str] = Query(None, description="Filter by strategy type"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: UserProfile = Depends(get_current_user)
):
    """Get public strategies that can be cloned"""
    try:
        strategies = await get_public_strategies(
            user_id=current_user.id,
            strategy_type=strategy_type,
            limit=limit * page  # Simple pagination for now
        )
        
        # Add parameter counts and convert to public response format
        public_strategies = []
        for strategy in strategies:
            try:
                # Note: Can't get parameters for other users' strategies without access
                parameter_count = 0  # Will be updated in future with public parameter info
            except:
                parameter_count = 0
            
            public_strategies.append({
                "id": strategy.id,
                "name": strategy.name,
                "description": strategy.description,
                "strategy_type": strategy.strategy_type,
                "risk_level": strategy.risk_level,
                "created_by": strategy.created_by,
                "created_at": strategy.created_at,
                "parameter_count": parameter_count
            })
        
        # Apply pagination
        paginated_result = apply_pagination(public_strategies, page, limit)
        
        return PublicStrategyListResponse(
            strategies=paginated_result["data"],
            total_count=paginated_result["pagination"]["total"],
            page=paginated_result["pagination"]["page"],
            page_size=paginated_result["pagination"]["limit"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get public strategies: {str(e)}")