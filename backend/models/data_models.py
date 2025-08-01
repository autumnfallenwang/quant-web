# models/data_models.py - Data API request/response models
"""
Pydantic models for data infrastructure API endpoints.
Defines request and response schemas for data operations.
"""
# Standard library imports
from typing import Optional, Literal

# Third-party imports
from pydantic import BaseModel, Field, ConfigDict


class DataRefreshRequest(BaseModel):
    """Request model for data refresh operations"""
    days_back: int = Field(30, ge=1, le=365, description="Days of data to refresh")
    interval: Literal["1d", "1h"] = Field("1d", description="Data interval")
    asset_type: Optional[Literal["stocks", "crypto", "all"]] = Field("all", description="Asset type to refresh")
    async_mode: bool = Field(True, description="Run in background")


class SymbolAddRequest(BaseModel):
    """Request model for adding symbols"""
    symbol: str = Field(..., description="Symbol to add (e.g., 'NVDA', 'SOL-USD')")
    asset_type: Literal["auto", "stock", "crypto"] = Field("auto", description="Asset type")


class DataRefreshResponse(BaseModel):
    """Response model for data refresh operations"""
    message: str
    status: Literal["started", "completed"]
    estimated_duration: Optional[str] = None
    symbols_count: Optional[int] = None
    result: Optional[dict] = None


class SymbolResponse(BaseModel):
    """Response model for symbol operations"""
    message: str
    symbol: str
    asset_type: Optional[str] = None


class SymbolListResponse(BaseModel):
    """Response model for symbol list operations"""
    model_config = ConfigDict(exclude_none=True)
    
    stocks: Optional[list[str]] = None
    crypto: Optional[list[str]] = None
    total: int


class CoverageResponse(BaseModel):
    """Response model for coverage operations"""
    symbol: Optional[str] = None
    coverage: Optional[dict] = None
    stocks: Optional[dict] = None
    crypto: Optional[dict] = None
    total_symbols: Optional[int] = None
    coverage_stats: Optional[dict] = None


class ScheduledRefreshResponse(BaseModel):
    """Response model for scheduled refresh operations"""
    message: str
    schedule: str
    status: Literal["started"]