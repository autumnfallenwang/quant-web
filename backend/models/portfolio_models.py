# models/portfolio_models.py - Portfolio API request/response models
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Literal
from datetime import datetime
from decimal import Decimal

# Type definitions
TradeType = Literal["buy", "sell"]
AnalysisType = Literal["quick", "comprehensive"]

# ===== PORTFOLIO MODELS =====

class PortfolioCreateRequest(BaseModel):
    name: str = Field(..., description="Portfolio name", max_length=100)
    description: Optional[str] = Field(default="", description="Portfolio description", max_length=500)
    initial_cash: Decimal = Field(default=Decimal('10000.00'), description="Initial cash balance", ge=0)

class PortfolioUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, description="Portfolio name", max_length=100)
    description: Optional[str] = Field(None, description="Portfolio description", max_length=500)

class PortfolioResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_by: int
    workspace_id: int
    initial_cash: Decimal
    current_cash: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    # Calculated fields (when available)
    position_count: Optional[int] = None
    total_value: Optional[Decimal] = None
    total_return: Optional[Decimal] = None
    return_percentage: Optional[Decimal] = None

class PortfolioListResponse(BaseModel):
    portfolios: List[PortfolioResponse]
    total_count: int
    page: int
    page_size: int

class PortfolioSummaryResponse(BaseModel):
    id: int
    name: str
    current_cash: Decimal
    position_count: int
    total_value: Decimal
    total_return: Decimal
    return_percentage: Decimal
    updated_at: datetime

# ===== POSITION MODELS =====

class PositionResponse(BaseModel):
    id: int
    symbol: str
    quantity: Decimal
    average_price: Decimal
    current_price: Optional[Decimal]
    position_type: str
    opened_at: datetime
    updated_at: datetime
    
    # Calculated fields
    market_value: Optional[Decimal] = None
    unrealized_pnl: Optional[Decimal] = None
    unrealized_pnl_percentage: Optional[Decimal] = None

class PositionListResponse(BaseModel):
    positions: List[PositionResponse]
    total_count: int

# ===== TRANSACTION MODELS =====

class TransactionResponse(BaseModel):
    id: int
    transaction_type: str
    symbol: str
    quantity: Decimal
    price: Decimal
    total_amount: Decimal
    fees: Decimal
    notes: Optional[str]
    executed_at: datetime
    created_at: datetime

class TransactionListResponse(BaseModel):
    transactions: List[TransactionResponse]
    total_count: int
    page: int
    page_size: int

# ===== TRADE MODELS =====

class TradeSimulationRequest(BaseModel):
    symbol: str = Field(..., description="Stock symbol", max_length=10)
    quantity: Decimal = Field(..., description="Number of shares", gt=0)
    price: Decimal = Field(..., description="Price per share", gt=0)
    trade_type: TradeType = Field(..., description="Trade type: buy or sell")

class TradeExecutionRequest(BaseModel):
    symbol: str = Field(..., description="Stock symbol", max_length=10)
    quantity: Decimal = Field(..., description="Number of shares", gt=0)
    price: Decimal = Field(..., description="Price per share", gt=0)
    trade_type: TradeType = Field(..., description="Trade type: buy or sell")
    notes: Optional[str] = Field(default=None, description="Trade notes", max_length=500)

class TradeSimulationResponse(BaseModel):
    can_execute: bool
    error: Optional[str] = None
    
    # Trade details
    trade_impact: Optional[Dict] = None
    portfolio_before: Optional[Dict] = None
    portfolio_after: Optional[Dict] = None
    
    # Warnings or recommendations
    warnings: Optional[List[str]] = None

class TradeExecutionResponse(BaseModel):
    transaction_id: int
    trade_type: str
    symbol: str
    quantity: Decimal
    price: Decimal
    total_amount: Decimal
    fees: Decimal
    executed_at: datetime
    
    # Updated portfolio summary
    portfolio_cash: Decimal
    position_created: bool = False
    position_updated: bool = False
    position_closed: bool = False

# ===== ANALYSIS MODELS =====

class PortfolioAnalysisRequest(BaseModel):
    analysis_type: AnalysisType = Field(default="quick", description="Type of analysis to perform")
    include_risk_metrics: bool = Field(default=True, description="Include risk calculations")
    include_allocation: bool = Field(default=True, description="Include allocation breakdown")

class PortfolioAnalysisResponse(BaseModel):
    portfolio_id: int
    analysis_type: str
    analysis_timestamp: datetime
    
    # Core metrics
    total_value: Decimal
    cash_balance: Decimal
    positions_value: Decimal
    total_return: Optional[Decimal] = None
    return_percentage: Optional[Decimal] = None
    
    # Allocation breakdown
    allocation: Optional[Dict[str, Decimal]] = None
    
    # Risk metrics
    risk_metrics: Optional[Dict[str, Decimal]] = None
    
    # Position details
    positions: Optional[List[Dict]] = None
    
    # For comprehensive analysis (job-based)
    job_id: Optional[str] = None
    recommendations: Optional[List[str]] = None
    transaction_analysis: Optional[Dict] = None

class PortfolioValidationResponse(BaseModel):
    portfolio_id: int
    is_valid: bool
    issues: List[str]
    warnings: List[str]
    validation_timestamp: datetime

# ===== BULK OPERATIONS =====

class BulkTradeRequest(BaseModel):
    trades: List[TradeExecutionRequest] = Field(..., description="List of trades to execute", max_items=50)
    execute_all_or_none: bool = Field(default=True, description="Execute all trades or none if any fail")

class BulkTradeResponse(BaseModel):
    job_id: str
    total_trades: int
    status: str
    estimated_duration: Optional[int] = None

# ===== REBALANCING MODELS =====

class PortfolioRebalanceRequest(BaseModel):
    target_allocation: Dict[str, Decimal] = Field(..., description="Target allocation percentages by symbol")
    cash_threshold: Decimal = Field(default=Decimal('100.00'), description="Minimum cash to maintain")
    max_trade_size: Optional[Decimal] = Field(default=None, description="Maximum single trade size")

class PortfolioRebalanceResponse(BaseModel):
    job_id: str
    target_allocation: Dict[str, Decimal]
    proposed_trades: List[Dict]
    estimated_cost: Decimal
    status: str

# ===== PERFORMANCE MODELS =====

class PortfolioPerformanceRequest(BaseModel):
    start_date: Optional[datetime] = Field(default=None, description="Start date for performance calculation")
    end_date: Optional[datetime] = Field(default=None, description="End date for performance calculation")
    benchmark_symbol: Optional[str] = Field(default="SPY", description="Benchmark symbol for comparison")

class PortfolioPerformanceResponse(BaseModel):
    portfolio_id: int
    period_start: datetime
    period_end: datetime
    
    # Performance metrics
    total_return: Decimal
    annualized_return: Decimal
    volatility: Decimal
    sharpe_ratio: Optional[Decimal] = None
    max_drawdown: Decimal
    
    # Benchmark comparison
    benchmark_return: Optional[Decimal] = None
    alpha: Optional[Decimal] = None
    beta: Optional[Decimal] = None
    
    # Period breakdown
    monthly_returns: Optional[List[Dict]] = None

# ===== ERROR MODELS =====

class PortfolioErrorResponse(BaseModel):
    error: str
    error_code: str
    details: Optional[Dict] = None
    suggestions: Optional[List[str]] = None