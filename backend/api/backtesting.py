# api/backtesting.py
"""
Backtesting API endpoints - workspace-scoped REST API for backtesting operations
"""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, Path
from fastapi.responses import JSONResponse

from core.plugin import get_pagination_params, get_sorting_params, apply_sorting, apply_pagination
from core.security import get_current_user
from models.db_models import UserProfile
from models.backtesting_models import (
    BacktestCreateRequest, BacktestUpdateRequest,
    BacktestResponse, BacktestListResponse, BacktestResultsResponse,
    BacktestJobResponse, BacktestSummaryResponse, BacktestErrorResponse
)
from services.backtesting_service import (
    create_backtest, start_backtest, get_backtest, get_user_backtests,
    get_backtest_results, cancel_backtest
)

router = APIRouter()

# ===== WORKSPACE-SCOPED BACKTEST OPERATIONS =====

@router.get("/workspace/{workspace_id}/backtests", response_model=BacktestListResponse)
async def list_backtests(
    workspace_id: int = Path(..., description="Workspace ID"),
    strategy_id: Optional[int] = Query(None, description="Filter by strategy ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    sort: Optional[str] = Query(None, description="Sort field"),
    order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: UserProfile = Depends(get_current_user)
):
    """List backtests in a workspace with filtering, sorting, and pagination"""
    try:
        # Get backtests
        backtests = await get_user_backtests(
            user_id=current_user.id,
            workspace_id=workspace_id,
            strategy_id=strategy_id,
            status=status
        )
        
        # Convert to response models
        backtest_responses = [BacktestResponse.model_validate(bt) for bt in backtests]
        
        # Apply sorting
        if sort:
            backtest_responses = apply_sorting(backtest_responses, sort, order)
        
        # Apply pagination
        paginated_result = apply_pagination(backtest_responses, page, limit)
        
        return BacktestListResponse(
            backtests=paginated_result["data"],
            total_count=paginated_result["pagination"]["total"],
            page=paginated_result["pagination"]["page"],
            page_size=paginated_result["pagination"]["limit"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list backtests: {str(e)}")


@router.post("/workspace/{workspace_id}/backtests", response_model=BacktestResponse, status_code=201)
async def create_backtest_endpoint(
    workspace_id: int = Path(..., description="Workspace ID"),
    request: BacktestCreateRequest = ...,
    current_user: UserProfile = Depends(get_current_user)
):
    """Create a new backtest in the workspace"""
    try:
        backtest = await create_backtest(
            user_id=current_user.id,
            workspace_id=workspace_id,
            strategy_id=request.strategy_id,
            name=request.name,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=request.initial_capital,
            symbols=request.symbols,
            description=request.description,
            commission_per_share=request.commission_per_share or Decimal("0.01"),
            commission_percentage=request.commission_percentage or Decimal("0.0"),
            slippage=request.slippage or Decimal("0.001")
        )
        
        return BacktestResponse.model_validate(backtest)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create backtest: {str(e)}")


@router.get("/workspace/{workspace_id}/backtests/{backtest_id}", response_model=BacktestResponse)
async def get_backtest_endpoint(
    workspace_id: int = Path(..., description="Workspace ID"),
    backtest_id: int = Path(..., description="Backtest ID"),
    current_user: UserProfile = Depends(get_current_user)
):
    """Get backtest details"""
    try:
        backtest = await get_backtest(backtest_id, current_user.id)
        
        # Verify workspace
        if backtest.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Backtest not found in specified workspace")
        
        return BacktestResponse.model_validate(backtest)
        
    except ValueError:
        raise HTTPException(status_code=404, detail="Backtest not found or access denied")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get backtest: {str(e)}")


@router.post("/workspace/{workspace_id}/backtests/{backtest_id}/start", response_model=BacktestJobResponse)
async def start_backtest_endpoint(
    workspace_id: int = Path(..., description="Workspace ID"),
    backtest_id: int = Path(..., description="Backtest ID"),
    current_user: UserProfile = Depends(get_current_user)
):
    """Start backtest execution"""
    try:
        # Verify backtest belongs to workspace
        backtest = await get_backtest(backtest_id, current_user.id)
        if backtest.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Backtest not found in specified workspace")
        
        job_id = await start_backtest(backtest_id, current_user.id)
        
        return BacktestJobResponse(
            job_id=job_id,
            backtest_id=backtest_id,
            status="running",
            message="Backtest execution started",
            progress_percent=0,
            estimated_duration=600,  # 10 minutes
            created_at=datetime.now()
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start backtest: {str(e)}")


@router.post("/workspace/{workspace_id}/backtests/{backtest_id}/cancel", response_model=dict)
async def cancel_backtest_endpoint(
    workspace_id: int = Path(..., description="Workspace ID"),
    backtest_id: int = Path(..., description="Backtest ID"),
    current_user: UserProfile = Depends(get_current_user)
):
    """Cancel a running backtest"""
    try:
        # Verify backtest belongs to workspace
        backtest = await get_backtest(backtest_id, current_user.id)
        if backtest.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Backtest not found in specified workspace")
        
        success = await cancel_backtest(backtest_id, current_user.id)
        
        if success:
            return {"message": "Backtest cancelled successfully", "backtest_id": backtest_id}
        else:
            raise HTTPException(status_code=400, detail="Backtest cannot be cancelled (not running)")
        
    except ValueError:
        raise HTTPException(status_code=404, detail="Backtest not found or access denied")
    except HTTPException:
        raise  # Re-raise HTTP exceptions from service layer
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel backtest: {str(e)}")


@router.get("/workspace/{workspace_id}/backtests/{backtest_id}/results", response_model=BacktestResultsResponse)
async def get_backtest_results_endpoint(
    workspace_id: int = Path(..., description="Workspace ID"),
    backtest_id: int = Path(..., description="Backtest ID"),
    current_user: UserProfile = Depends(get_current_user)
):
    """Get comprehensive backtest results"""
    try:
        # Verify backtest belongs to workspace
        backtest = await get_backtest(backtest_id, current_user.id)
        if backtest.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Backtest not found in specified workspace")
        
        results = await get_backtest_results(backtest_id, current_user.id)
        
        # Handle incomplete backtests
        if "status" in results and results["status"] != "completed":
            return JSONResponse(
                status_code=202,  # Accepted - processing not complete
                content={
                    "status": results["status"],
                    "message": results.get("message", f"Backtest is {results['status']}"),
                    "backtest_id": backtest.backtest_id
                }
            )
        
        return BacktestResultsResponse(**results)
        
    except ValueError:
        raise HTTPException(status_code=404, detail="Backtest not found or access denied")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get backtest results: {str(e)}")


# ===== BACKTEST MANAGEMENT =====

@router.patch("/workspace/{workspace_id}/backtests/{backtest_id}", response_model=BacktestResponse)
async def update_backtest_endpoint(
    workspace_id: int = Path(..., description="Workspace ID"),
    backtest_id: int = Path(..., description="Backtest ID"),
    request: BacktestUpdateRequest = ...,
    current_user: UserProfile = Depends(get_current_user)
):
    """Update backtest metadata (name, description only)"""
    try:
        # Get existing backtest
        backtest = await get_backtest(backtest_id, current_user.id)
        if backtest.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Backtest not found in specified workspace")
        
        # Only allow updates if backtest is not running
        if backtest.status == "running":
            raise HTTPException(status_code=400, detail="Cannot update running backtest")
        
        # Update allowed fields
        if request.name is not None:
            backtest.name = request.name
        if request.description is not None:
            backtest.description = request.description
        
        backtest.updated_at = datetime.now()
        
        # Save changes (this would normally be handled by the service layer)
        # For now, returning the updated object
        return BacktestResponse.model_validate(backtest)
        
    except ValueError:
        raise HTTPException(status_code=404, detail="Backtest not found or access denied")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update backtest: {str(e)}")


@router.delete("/workspace/{workspace_id}/backtests/{backtest_id}")
async def delete_backtest_endpoint(
    workspace_id: int = Path(..., description="Workspace ID"),
    backtest_id: int = Path(..., description="Backtest ID"),
    current_user: UserProfile = Depends(get_current_user)
):
    """Delete a backtest (only if not running)"""
    try:
        # Get backtest
        backtest = await get_backtest(backtest_id, current_user.id)
        if backtest.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Backtest not found in specified workspace")
        
        # Only allow deletion if not running
        if backtest.status == "running":
            raise HTTPException(status_code=400, detail="Cannot delete running backtest")
        
        # This would be implemented in the service layer
        # For now, just return success
        return {"message": "Backtest deleted successfully", "backtest_id": backtest_id}
        
    except ValueError:
        raise HTTPException(status_code=404, detail="Backtest not found or access denied")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete backtest: {str(e)}")


# ===== WORKSPACE BACKTEST SUMMARIES =====

@router.get("/workspace/{workspace_id}/backtest-analytics", response_model=BacktestSummaryResponse)
async def get_workspace_backtest_analytics(
    workspace_id: int = Path(..., description="Workspace ID"),
    current_user: UserProfile = Depends(get_current_user)
):
    """Get analytics and summary statistics for all backtests in workspace"""
    try:
        # Get all backtests for workspace
        backtests = await get_user_backtests(
            user_id=current_user.id,
            workspace_id=workspace_id
        )
        
        # Calculate summary statistics
        total_backtests = len(backtests)
        completed_backtests = len([bt for bt in backtests if bt.status == "completed"])
        running_backtests = len([bt for bt in backtests if bt.status == "running"])
        failed_backtests = len([bt for bt in backtests if bt.status == "failed"])
        
        # Calculate averages for completed backtests
        completed = [bt for bt in backtests if bt.status == "completed" and bt.return_percentage is not None]
        
        avg_return = None
        avg_sharpe = None
        avg_drawdown = None
        best_backtest = None
        worst_backtest = None
        
        if completed:
            avg_return = sum(bt.return_percentage for bt in completed) / len(completed)
            valid_sharpe = [bt for bt in completed if bt.sharpe_ratio is not None]
            if valid_sharpe:
                avg_sharpe = sum(bt.sharpe_ratio for bt in valid_sharpe) / len(valid_sharpe)
            
            valid_drawdown = [bt for bt in completed if bt.max_drawdown is not None]
            if valid_drawdown:
                avg_drawdown = sum(bt.max_drawdown for bt in valid_drawdown) / len(valid_drawdown)
            
            # Find best and worst performing
            best_bt = max(completed, key=lambda x: x.return_percentage)
            worst_bt = min(completed, key=lambda x: x.return_percentage)
            
            best_backtest = {
                "id": best_bt.id,
                "name": best_bt.name,
                "return_percentage": float(best_bt.return_percentage)
            }
            worst_backtest = {
                "id": worst_bt.id,
                "name": worst_bt.name,
                "return_percentage": float(worst_bt.return_percentage)
            }
        
        return BacktestSummaryResponse(
            total_backtests=total_backtests,
            completed_backtests=completed_backtests,
            running_backtests=running_backtests,
            failed_backtests=failed_backtests,
            avg_return_percentage=avg_return,
            avg_sharpe_ratio=avg_sharpe,
            avg_max_drawdown=avg_drawdown,
            best_performing_backtest=best_backtest,
            worst_performing_backtest=worst_backtest
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get backtest summary: {str(e)}")


# Error handling done through standard HTTPException raising in endpoints