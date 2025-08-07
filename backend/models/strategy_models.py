# models/strategy_models.py
"""
Pydantic models for Strategy API requests and responses
"""
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator


# Base Models
class StrategyParameterBase(BaseModel):
    parameter_name: str = Field(..., max_length=100, description="Parameter name")
    parameter_type: str = Field(..., description="Parameter type: int, float, string, boolean")
    default_value: str = Field(..., description="Default parameter value")
    current_value: str = Field(..., description="Current parameter value")
    min_value: Optional[str] = Field(None, description="Minimum value for numeric parameters")
    max_value: Optional[str] = Field(None, description="Maximum value for numeric parameters") 
    description: Optional[str] = Field(None, max_length=500, description="Parameter description")
    is_required: bool = Field(True, description="Whether parameter is required")


class SignalBase(BaseModel):
    signal_type: str = Field(..., description="Signal type: buy, sell, hold, arbitrage")
    symbol: str = Field(..., max_length=10, description="Trading symbol")
    signal_strength: Decimal = Field(..., ge=0, le=1, description="Signal strength (0.0-1.0)")
    price: Decimal = Field(..., gt=0, description="Price associated with signal")
    confidence_score: Decimal = Field(..., ge=0, le=1, description="Confidence score (0.0-1.0)")
    signal_data: Optional[Dict[str, Any]] = Field(None, description="Additional signal metadata")


# Request Models
class StrategyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Strategy name")
    strategy_type: str = Field(..., description="Strategy type: momentum, mean_reversion, arbitrage, custom")
    description: Optional[str] = Field(None, max_length=500, description="Strategy description")
    strategy_code: Optional[str] = Field(None, description="Custom strategy code (for custom type)")
    risk_level: str = Field("medium", description="Risk level: low, medium, high")
    is_public: bool = Field(False, description="Whether strategy is publicly visible")
    parameters: Optional[List[Dict[str, Any]]] = Field(None, description="Strategy parameters")

    @field_validator('strategy_type')
    @classmethod
    def validate_strategy_type(cls, v):
        allowed_types = ["momentum", "mean_reversion", "arbitrage", "custom"]
        if v not in allowed_types:
            raise ValueError(f"Strategy type must be one of: {', '.join(allowed_types)}")
        return v

    @field_validator('risk_level')
    @classmethod
    def validate_risk_level(cls, v):
        allowed_levels = ["low", "medium", "high"]
        if v not in allowed_levels:
            raise ValueError(f"Risk level must be one of: {', '.join(allowed_levels)}")
        return v


class StrategyUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Strategy name")
    description: Optional[str] = Field(None, max_length=500, description="Strategy description")
    strategy_code: Optional[str] = Field(None, description="Custom strategy code")
    risk_level: Optional[str] = Field(None, description="Risk level: low, medium, high")
    is_active: Optional[bool] = Field(None, description="Whether strategy is active")

    @field_validator('risk_level')
    @classmethod
    def validate_risk_level(cls, v):
        if v is not None:
            allowed_levels = ["low", "medium", "high"]
            if v not in allowed_levels:
                raise ValueError(f"Risk level must be one of: {', '.join(allowed_levels)}")
        return v


class ParameterUpdateRequest(BaseModel):
    current_value: str = Field(..., description="New parameter value")


class AnalysisRequest(BaseModel):
    analysis_type: str = Field("quick", description="Analysis type: quick or comprehensive")
    symbols: Optional[List[str]] = Field(None, description="List of symbols to analyze (default: top 5 stocks)", max_length=50)
    include_risk_metrics: bool = Field(True, description="Include risk analysis")
    include_allocation: bool = Field(True, description="Include allocation analysis")

    @field_validator('analysis_type')
    @classmethod
    def validate_analysis_type(cls, v):
        allowed_types = ["quick", "comprehensive"]
        if v not in allowed_types:
            raise ValueError(f"Analysis type must be one of: {', '.join(allowed_types)}")
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


class BacktestRequest(BaseModel):
    start_date: datetime = Field(..., description="Backtest start date")
    end_date: datetime = Field(..., description="Backtest end date")
    initial_capital: Decimal = Field(Decimal("100000.00"), gt=0, description="Initial capital for backtest")

    @field_validator('end_date')
    @classmethod
    def validate_end_date(cls, v, info):
        start_date = info.data.get('start_date')
        if start_date and v <= start_date:
            raise ValueError("End date must be after start date")
        return v


class SignalGenerationRequest(BaseModel):
    symbols: List[str] = Field(..., description="List of symbols to generate signals for", min_length=1, max_length=50)
    lookback_days: int = Field(30, ge=1, le=365, description="Days of historical data to use for signal generation")

    @field_validator('symbols')
    @classmethod
    def validate_symbols(cls, v):
        if len(v) == 0:
            raise ValueError("At least one symbol is required")
        if len(v) > 50:
            raise ValueError("Maximum 50 symbols allowed")
        for symbol in v:
            if not isinstance(symbol, str) or len(symbol.strip()) == 0:
                raise ValueError("All symbols must be non-empty strings")
            if len(symbol) > 10:
                raise ValueError("Symbol length cannot exceed 10 characters")
        return v


class CloneStrategyRequest(BaseModel):
    new_name: str = Field(..., min_length=1, max_length=100, description="Name for cloned strategy")
    target_workspace_id: Optional[int] = Field(None, description="Target workspace ID (default: same as source)")


# Response Models
class StrategyParameterResponse(StrategyParameterBase):
    id: int
    strategy_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StrategyResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    strategy_type: str
    strategy_code: Optional[str]
    is_active: bool
    is_public: bool
    risk_level: str
    workspace_id: int
    created_by: int
    created_at: datetime
    updated_at: datetime
    parameter_count: Optional[int] = Field(None, description="Number of parameters")

    model_config = ConfigDict(from_attributes=True)


class StrategyListResponse(BaseModel):
    strategies: List[StrategyResponse]
    total_count: int
    page: int
    page_size: int


class SignalResponse(SignalBase):
    id: int
    strategy_id: int
    is_executed: bool
    executed_at: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SignalListResponse(BaseModel):
    signals: List[SignalResponse]
    total_count: int


class PerformanceResponse(BaseModel):
    id: int
    strategy_id: int
    period_start: datetime
    period_end: datetime
    total_return: Decimal
    return_percentage: Decimal
    sharpe_ratio: Optional[Decimal]
    max_drawdown: Optional[Decimal]
    volatility: Optional[Decimal]
    win_rate: Optional[Decimal]
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_trade_return: Optional[Decimal]
    performance_data: Optional[Dict[str, Any]]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PerformanceListResponse(BaseModel):
    performance_records: List[PerformanceResponse]
    total_count: int


class QuickAnalysisResponse(BaseModel):
    strategy_id: int
    performance_metrics: Dict[str, Any]
    risk_metrics: Dict[str, Any]
    signal_analysis: Dict[str, Any]
    recommendations: List[str]
    analysis_timestamp: datetime


class ComprehensiveAnalysisResponse(BaseModel):
    strategy_id: int
    analysis_type: str
    analysis_timestamp: datetime
    total_value: Decimal = Field(Decimal("0"), description="Placeholder for job-based analysis")
    cash_balance: Decimal = Field(Decimal("0"), description="Placeholder for job-based analysis")
    positions_value: Decimal = Field(Decimal("0"), description="Placeholder for job-based analysis")
    job_id: str = Field(..., description="Job ID for tracking analysis progress")


class BacktestResponse(BaseModel):
    strategy_id: int
    analysis_type: str = Field("backtest", description="Analysis type")
    analysis_timestamp: datetime
    total_value: Decimal = Field(Decimal("0"), description="Placeholder for job-based backtest")
    cash_balance: Decimal = Field(Decimal("0"), description="Placeholder for job-based backtest")
    positions_value: Decimal = Field(Decimal("0"), description="Placeholder for job-based backtest")
    job_id: str = Field(..., description="Job ID for tracking backtest progress")


class ValidationResponse(BaseModel):
    strategy_id: int
    is_valid: bool
    issues: List[str]
    warnings: List[str]
    validation_timestamp: datetime


class PublicStrategyResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    strategy_type: str
    risk_level: str
    created_by: int
    created_at: datetime
    parameter_count: Optional[int] = Field(None, description="Number of parameters")

    model_config = ConfigDict(from_attributes=True)


class PublicStrategyListResponse(BaseModel):
    strategies: List[PublicStrategyResponse]
    total_count: int
    page: int
    page_size: int