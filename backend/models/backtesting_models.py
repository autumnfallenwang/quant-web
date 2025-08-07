# models/backtesting_models.py
"""
Pydantic models for Backtesting API requests and responses
"""
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator


# Request Models
class BacktestCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Backtest name")
    strategy_id: int = Field(..., description="ID of strategy to backtest")
    start_date: datetime = Field(..., description="Backtest start date")
    end_date: datetime = Field(..., description="Backtest end date")
    initial_capital: Decimal = Field(..., gt=0, description="Initial capital amount")
    symbols: Optional[List[str]] = Field(None, description="Symbols to backtest (default: top 5)", max_length=50)
    description: Optional[str] = Field(None, max_length=500, description="Backtest description")
    
    # Trading configuration
    commission_per_share: Optional[Decimal] = Field(Decimal("0.01"), ge=0, description="Commission per share")
    commission_percentage: Optional[Decimal] = Field(Decimal("0.0"), ge=0, le=0.1, description="Commission percentage") 
    slippage: Optional[Decimal] = Field(Decimal("0.001"), ge=0, le=0.1, description="Slippage percentage")

    @field_validator('end_date')
    @classmethod
    def validate_end_date(cls, v, info):
        start_date = info.data.get('start_date')
        if start_date and v <= start_date:
            raise ValueError("End date must be after start date")
        return v

    @field_validator('symbols')
    @classmethod
    def validate_symbols(cls, v):
        if v is not None:
            if len(v) == 0:
                raise ValueError("Symbols list cannot be empty if provided")
            if len(v) > 50:
                raise ValueError("Maximum 50 symbols allowed")
            for symbol in v:
                if not isinstance(symbol, str) or len(symbol.strip()) == 0:
                    raise ValueError("All symbols must be non-empty strings")
                if len(symbol) > 10:
                    raise ValueError("Symbol length cannot exceed 10 characters")
        return v


class BacktestUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Backtest name")
    description: Optional[str] = Field(None, max_length=500, description="Backtest description")


# Response Models
class BacktestResponse(BaseModel):
    id: int
    backtest_id: str
    name: str
    description: Optional[str]
    strategy_id: int
    workspace_id: int
    
    # Configuration
    start_date: datetime
    end_date: datetime
    initial_capital: Decimal
    symbols: List[str]
    commission_per_share: Decimal
    commission_percentage: Decimal
    slippage: Decimal
    
    # Results (None if not completed)
    status: str
    total_return: Optional[Decimal]
    return_percentage: Optional[Decimal]
    sharpe_ratio: Optional[Decimal]
    max_drawdown: Optional[Decimal]
    volatility: Optional[Decimal]
    total_trades: int
    win_rate: Optional[Decimal]
    
    # Execution metadata
    job_id: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)


class BacktestListResponse(BaseModel):
    backtests: List[BacktestResponse]
    total_count: int
    page: int
    page_size: int


class BacktestTradeResponse(BaseModel):
    id: int
    symbol: str
    trade_type: str
    quantity: int
    price: Decimal
    commission: Decimal
    signal_timestamp: datetime
    execution_timestamp: datetime
    signal_strength: Optional[Decimal]
    confidence_score: Optional[Decimal]
    
    model_config = ConfigDict(from_attributes=True)


class BacktestDailyMetricResponse(BaseModel):
    date: datetime
    portfolio_value: Decimal
    daily_return: Decimal
    cumulative_return: Decimal
    drawdown: Decimal
    trades_executed: int
    positions_count: int
    
    model_config = ConfigDict(from_attributes=True)


class BacktestPositionResponse(BaseModel):
    symbol: str
    quantity: int
    avg_price: Decimal
    current_price: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    total_pnl: Decimal
    
    model_config = ConfigDict(from_attributes=True)


class BacktestResultsResponse(BaseModel):
    backtest_id: str
    name: str
    strategy_id: int
    status: str
    start_date: datetime
    end_date: datetime
    symbols: List[str]
    
    # Summary metrics
    total_return: Optional[Decimal]
    return_percentage: Optional[Decimal]
    sharpe_ratio: Optional[Decimal]
    max_drawdown: Optional[Decimal]
    volatility: Optional[Decimal]
    total_trades: int
    win_rate: Optional[Decimal]
    
    # Detailed results
    trades: List[Dict[str, Any]]
    daily_metrics: List[Dict[str, Any]]
    final_positions: List[Dict[str, Any]]
    
    # Execution metadata
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    job_id: Optional[str]


class BacktestJobResponse(BaseModel):
    job_id: str
    backtest_id: int
    status: str
    message: str
    progress_percent: int
    estimated_duration: Optional[int]
    created_at: datetime
    
    
class BacktestSummaryResponse(BaseModel):
    """Summary statistics for multiple backtests"""
    total_backtests: int
    completed_backtests: int
    running_backtests: int
    failed_backtests: int
    
    avg_return_percentage: Optional[Decimal]
    avg_sharpe_ratio: Optional[Decimal]
    avg_max_drawdown: Optional[Decimal]
    
    best_performing_backtest: Optional[Dict[str, Any]]
    worst_performing_backtest: Optional[Dict[str, Any]]


# Error Response Models
class BacktestErrorResponse(BaseModel):
    error: str
    message: str
    backtest_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None