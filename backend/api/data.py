# api/data.py - Data engine infrastructure API endpoints
"""
Infrastructure-level API for market data operations.
User-agnostic endpoints for data access and management.
"""
# Standard library imports
from typing import Optional
import logging

# Third-party imports
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

# Local imports
from services.data_service import DataService
from models.data_models import (
    DataRefreshRequest, SymbolAddRequest, DataRefreshResponse,
    SymbolResponse, CoverageResponse, ScheduledRefreshResponse
)

router = APIRouter()
logger = logging.getLogger(__name__)

# Global service instance
data_service = DataService()

@router.post("/data/refresh", response_model=DataRefreshResponse)
async def refresh_data(
    background_tasks: BackgroundTasks,
    request: DataRefreshRequest
) -> DataRefreshResponse:
    """
    Refresh market data for tracked symbols
    
    Request body should contain:
    - **days_back**: Number of days to refresh (1-365, default: 30)
    - **interval**: Data interval ('1d' or '1h', default: '1d')
    - **asset_type**: 'stocks', 'crypto', or 'all' (default: 'all')
    - **async_mode**: Run in background (default: true)
    """
    
    if request.async_mode:
        # Run in background
        background_tasks.add_task(
            _background_refresh_data, 
            request.days_back, 
            request.interval,
            request.asset_type or "all"
        )
        
        tracked = data_service.get_tracked_symbols()
        return DataRefreshResponse(
            message="Data refresh started in background",
            estimated_duration=f"{tracked['total'] * 2} seconds",
            symbols_count=tracked['total'],
            status="started"
        )
    else:
        # Run synchronously (for smaller requests)
        try:
            if request.asset_type == "stocks":
                result = await data_service.refresh_sp500_only(request.days_back)
            elif request.asset_type == "crypto":
                result = await data_service.refresh_crypto_only(request.days_back)
            else:
                result = await data_service.refresh_all_symbols(request.days_back, request.interval)
            return DataRefreshResponse(
                message="Data refresh completed",
                result=result,
                status="completed"
            )
        except Exception as e:
            logger.error(f"Refresh failed: {e}")
            raise HTTPException(status_code=500, detail=f"Refresh failed: {str(e)}")

@router.get("/data/symbols")
async def get_tracked_symbols(
    asset_type: Optional[str] = Query(None, pattern="^(stocks|crypto)$", description="Filter by asset type")
):
    """
    Get list of all tracked symbols
    
    - **asset_type**: Filter by 'stocks' or 'crypto' (optional)
    """
    try:
        symbols = data_service.get_tracked_symbols()
        if asset_type:
            if asset_type == "stocks":
                return {"stocks": symbols["stocks"], "total": len(symbols["stocks"])}
            else:
                return {"crypto": symbols["crypto"], "total": len(symbols["crypto"])}
        return {
            "stocks": symbols["stocks"],
            "crypto": symbols["crypto"],
            "total": symbols["total"]
        }
    except Exception as e:
        logger.error(f"Error getting symbols: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/data/symbols", response_model=SymbolResponse)
async def add_symbol(request: SymbolAddRequest) -> SymbolResponse:
    """
    Add a symbol to the tracking list
    
    Request body should contain:
    - **symbol**: Symbol to track (e.g., 'NVDA', 'SOL-USD')
    - **asset_type**: 'auto', 'stock', or 'crypto' (default: 'auto')
    """
    try:
        data_service.add_symbol(request.symbol, request.asset_type)
        detected_type = "crypto" if "-USD" in request.symbol else "stock" if request.asset_type == "auto" else request.asset_type
        return SymbolResponse(
            message=f"Symbol {request.symbol} added successfully",
            symbol=request.symbol,
            asset_type=detected_type
        )
    except Exception as e:
        logger.error(f"Error adding symbol {request.symbol}: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/data/symbols/{symbol}", response_model=SymbolResponse)
async def remove_symbol(symbol: str) -> SymbolResponse:
    """
    Remove a symbol from tracking
    
    - **symbol**: Symbol to remove from tracking
    """
    try:
        data_service.remove_symbol(symbol)
        return SymbolResponse(
            message=f"Symbol {symbol} removed successfully",
            symbol=symbol
        )
    except Exception as e:
        logger.error(f"Error removing symbol {symbol}: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/data/coverage", response_model=CoverageResponse)
async def get_data_coverage(
    symbol: Optional[str] = Query(None, description="Get coverage for specific symbol")
) -> CoverageResponse:
    """
    Get data coverage summary
    
    - **symbol**: Get coverage for specific symbol (optional)
    """
    try:
        if symbol:
            # Get coverage for specific symbol using DataEngine directly
            from core.data_engine import DataEngine
            engine = DataEngine()
            coverage = engine.get_data_coverage(symbol, '1d')
            return CoverageResponse(symbol=symbol, coverage=coverage)
        else:
            # Get summary for all symbols
            coverage = await data_service.get_data_coverage_summary()
            return CoverageResponse(
                stocks=coverage.get("stocks"),
                crypto=coverage.get("crypto"),
                total_symbols=coverage.get("total_symbols"),
                coverage_stats=coverage.get("coverage_stats")
            )
    except Exception as e:
        logger.error(f"Error getting coverage: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Scheduled refresh endpoints for automation
@router.post("/data/refresh/daily", response_model=ScheduledRefreshResponse)
async def daily_refresh(background_tasks: BackgroundTasks) -> ScheduledRefreshResponse:
    """
    Daily scheduled refresh - last 7 days (for cron jobs)
    """
    background_tasks.add_task(_background_daily_refresh)
    return ScheduledRefreshResponse(
        message="Daily refresh started",
        schedule="Last 7 days",
        status="started"
    )

@router.post("/data/refresh/weekly", response_model=ScheduledRefreshResponse)
async def weekly_refresh(background_tasks: BackgroundTasks) -> ScheduledRefreshResponse:
    """
    Weekly scheduled refresh - last 30 days (for cron jobs)
    """
    background_tasks.add_task(_background_weekly_refresh)
    return ScheduledRefreshResponse(
        message="Weekly refresh started",
        schedule="Last 30 days",
        status="started"
    )

@router.post("/data/refresh/monthly", response_model=ScheduledRefreshResponse)
async def monthly_refresh(background_tasks: BackgroundTasks) -> ScheduledRefreshResponse:
    """
    Monthly scheduled refresh - last 90 days (for cron jobs)
    """
    background_tasks.add_task(_background_monthly_refresh)
    return ScheduledRefreshResponse(
        message="Monthly refresh started",
        schedule="Last 90 days",
        status="started"
    )



# Background task functions
async def _background_refresh_data(days_back: int, interval: str, asset_type: str):
    """Background task for data refresh"""
    try:
        if asset_type == "stocks":
            result = await data_service.refresh_stocks_only(days_back)
        elif asset_type == "crypto":
            result = await data_service.refresh_crypto_only(days_back)
        else:
            result = await data_service.refresh_all_symbols(days_back, interval)
        logger.info(f"Background {asset_type} refresh completed: {result['summary']}")
    except Exception as e:
        logger.error(f"Background {asset_type} refresh failed: {e}")

async def _background_daily_refresh():
    """Background daily refresh"""
    try:
        from services.data_service import daily_refresh
        result = await daily_refresh()
        logger.info(f"Daily refresh completed: {result['summary']}")
    except Exception as e:
        logger.error(f"Daily refresh failed: {e}")

async def _background_weekly_refresh():
    """Background weekly refresh"""
    try:
        from services.data_service import weekly_refresh  
        result = await weekly_refresh()
        logger.info(f"Weekly refresh completed: {result['summary']}")
    except Exception as e:
        logger.error(f"Weekly refresh failed: {e}")

async def _background_monthly_refresh():
    """Background monthly refresh"""
    try:
        from services.data_service import monthly_refresh
        result = await monthly_refresh()
        logger.info(f"Monthly refresh completed: {result['summary']}")
    except Exception as e:
        logger.error(f"Monthly refresh failed: {e}")