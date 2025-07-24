# api/data_refresh.py
"""
API endpoints for data refresh operations
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from typing import Optional, Dict, List
from datetime import date, timedelta
import asyncio
import logging

from services.data_refresh_service import DataRefreshService

router = APIRouter()
logger = logging.getLogger(__name__)

# Global service instance
refresh_service = DataRefreshService()

@router.post("/refresh/all")
async def refresh_all_data(
    background_tasks: BackgroundTasks,
    days_back: int = Query(30, ge=1, le=365, description="Days of data to refresh"),
    interval: str = Query("1d", regex="^(1d|1h)$", description="Data interval"),
    async_mode: bool = Query(True, description="Run in background")
) -> Dict:
    """
    Refresh data for all tracked symbols (S&P 500 + Top 20 Crypto)
    
    - **days_back**: Number of days to refresh (1-365)
    - **interval**: Data interval ('1d' or '1h') 
    - **async_mode**: Run in background if True
    """
    
    if async_mode:
        # Run in background
        background_tasks.add_task(
            _background_refresh_all, 
            days_back, 
            interval
        )
        
        return {
            "message": "Data refresh started in background",
            "estimated_duration": f"{len(refresh_service.get_tracked_symbols()['total']) * 2} seconds",
            "symbols_count": refresh_service.get_tracked_symbols()['total'],
            "status": "started"
        }
    else:
        # Run synchronously (for smaller requests)
        try:
            result = await refresh_service.refresh_all_symbols(days_back, interval)
            return {
                "message": "Data refresh completed",
                "result": result,
                "status": "completed"
            }
        except Exception as e:
            logger.error(f"Refresh failed: {e}")
            raise HTTPException(status_code=500, detail=f"Refresh failed: {str(e)}")

@router.post("/refresh/stocks")
async def refresh_stocks_only(
    background_tasks: BackgroundTasks,
    days_back: int = Query(30, ge=1, le=365),
    async_mode: bool = Query(True)
) -> Dict:
    """
    Refresh S&P 500 stocks only
    """
    
    if async_mode:
        background_tasks.add_task(
            _background_refresh_stocks,
            days_back
        )
        
        return {
            "message": "Stock data refresh started",
            "symbols_count": len(refresh_service.sp500_symbols),
            "status": "started"
        }
    else:
        try:
            result = await refresh_service.refresh_sp500_only(days_back)
            return {
                "message": "Stock refresh completed", 
                "result": result,
                "status": "completed"
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@router.post("/refresh/crypto")
async def refresh_crypto_only(
    background_tasks: BackgroundTasks,
    days_back: int = Query(30, ge=1, le=365),
    async_mode: bool = Query(True)
) -> Dict:
    """
    Refresh top 20 crypto only
    """
    
    if async_mode:
        background_tasks.add_task(
            _background_refresh_crypto,
            days_back
        )
        
        return {
            "message": "Crypto data refresh started",
            "symbols_count": len(refresh_service.top_cryptos), 
            "status": "started"
        }
    else:
        try:
            result = await refresh_service.refresh_crypto_only(days_back)
            return {
                "message": "Crypto refresh completed",
                "result": result,
                "status": "completed"
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@router.get("/symbols")
async def get_tracked_symbols() -> Dict:
    """
    Get list of all tracked symbols
    """
    return refresh_service.get_tracked_symbols()

@router.post("/symbols/add")
async def add_symbol(
    symbol: str = Query(..., description="Symbol to add (e.g., 'NVDA', 'SOL-USD')"),
    asset_type: str = Query("auto", regex="^(auto|stock|crypto)$")
) -> Dict:
    """
    Add a symbol to the tracking list
    """
    try:
        refresh_service.add_symbol(symbol, asset_type)
        return {
            "message": f"Symbol {symbol} added successfully",
            "symbol": symbol,
            "asset_type": asset_type if asset_type != "auto" else ("crypto" if "-USD" in symbol else "stock")
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/symbols/{symbol}")
async def remove_symbol(symbol: str) -> Dict:
    """
    Remove a symbol from tracking
    """
    try:
        refresh_service.remove_symbol(symbol)
        return {
            "message": f"Symbol {symbol} removed successfully",
            "symbol": symbol
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/coverage")
async def get_data_coverage() -> Dict:
    """
    Get data coverage summary for all tracked symbols
    """
    try:
        coverage = await refresh_service.get_data_coverage_summary()
        return coverage
    except Exception as e:
        logger.error(f"Error getting coverage: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Scheduled refresh endpoints (for cron jobs)
@router.post("/refresh/daily")
async def daily_refresh_endpoint(background_tasks: BackgroundTasks) -> Dict:
    """
    Daily refresh - last 7 days (designed for cron jobs)
    """
    background_tasks.add_task(_background_daily_refresh)
    
    return {
        "message": "Daily refresh started",
        "schedule": "Last 7 days",
        "status": "started"
    }

@router.post("/refresh/weekly") 
async def weekly_refresh_endpoint(background_tasks: BackgroundTasks) -> Dict:
    """
    Weekly refresh - last 30 days (designed for cron jobs)
    """
    background_tasks.add_task(_background_weekly_refresh)
    
    return {
        "message": "Weekly refresh started",
        "schedule": "Last 30 days", 
        "status": "started"
    }

@router.post("/refresh/monthly")
async def monthly_refresh_endpoint(background_tasks: BackgroundTasks) -> Dict:
    """
    Monthly refresh - last 90 days (designed for cron jobs)
    """
    background_tasks.add_task(_background_monthly_refresh)
    
    return {
        "message": "Monthly refresh started",
        "schedule": "Last 90 days",
        "status": "started"
    }

# Background task functions
async def _background_refresh_all(days_back: int, interval: str):
    """Background task for full refresh"""
    try:
        result = await refresh_service.refresh_all_symbols(days_back, interval)
        logger.info(f"Background refresh completed: {result['summary']}")
    except Exception as e:
        logger.error(f"Background refresh failed: {e}")

async def _background_refresh_stocks(days_back: int):
    """Background task for stocks refresh"""
    try:
        result = await refresh_service.refresh_sp500_only(days_back)
        logger.info(f"Background stocks refresh completed: {result['summary']}")
    except Exception as e:
        logger.error(f"Background stocks refresh failed: {e}")

async def _background_refresh_crypto(days_back: int):
    """Background task for crypto refresh"""
    try:
        result = await refresh_service.refresh_crypto_only(days_back)
        logger.info(f"Background crypto refresh completed: {result['summary']}")
    except Exception as e:
        logger.error(f"Background crypto refresh failed: {e}")

async def _background_daily_refresh():
    """Background daily refresh"""
    try:
        from services.data_refresh_service import daily_refresh
        result = await daily_refresh()
        logger.info(f"Daily refresh completed: {result['summary']}")
    except Exception as e:
        logger.error(f"Daily refresh failed: {e}")

async def _background_weekly_refresh():
    """Background weekly refresh"""
    try:
        from services.data_refresh_service import weekly_refresh  
        result = await weekly_refresh()
        logger.info(f"Weekly refresh completed: {result['summary']}")
    except Exception as e:
        logger.error(f"Weekly refresh failed: {e}")

async def _background_monthly_refresh():
    """Background monthly refresh"""
    try:
        from services.data_refresh_service import monthly_refresh
        result = await monthly_refresh()
        logger.info(f"Monthly refresh completed: {result['summary']}")
    except Exception as e:
        logger.error(f"Monthly refresh failed: {e}")