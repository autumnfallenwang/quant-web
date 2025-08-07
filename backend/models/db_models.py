# models/db_models.py
import uuid
from datetime import datetime, UTC
from typing import Optional, List
from decimal import Decimal

from sqlalchemy import Column, JSON, String, Text, DECIMAL
from sqlmodel import SQLModel, Field, Relationship, UniqueConstraint

class IdentityUser(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    subject: str
    issuer: str = "local-idp"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    user_profile: Optional["UserProfile"] = Relationship(back_populates="identity_user")

    __table_args__ = (UniqueConstraint("subject", "issuer"),)

class UserProfile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="identityuser.id", unique=True)
    username: str = Field(index=True, unique=True)
    email: Optional[str] = None
    role: str = Field(default="user")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    identity_user: Optional[IdentityUser] = Relationship(back_populates="user_profile")
    workspace_memberships: List["WorkspaceMembership"] = Relationship(back_populates="user_profile")

class Job(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        sa_column=Column("job_id", String(36), unique=True, nullable=False)
    )
    job_type: str  # e.g., 'data_refresh_all', 'data_refresh_stocks', 'custom_analysis'
    status: str = Field(default="pending")  # pending, running, success, failed, cancelled
    result: Optional[dict] = Field(default=None, sa_column=Column(JSON))  # Enhanced: stores progress, metadata, errors
    priority: str = Field(default="normal")  # low, normal, high, urgent
    estimated_duration: Optional[int] = Field(default=None)  # seconds
    actual_duration: Optional[int] = Field(default=None)  # seconds
    retry_count: int = Field(default=0)  # Number of retry attempts
    max_retries: int = Field(default=3)  # Maximum retry attempts
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    scheduled_at: Optional[datetime] = Field(default=None)  # For scheduled jobs

    workspace_id: int = Field(foreign_key="workspace.id")
    created_by: Optional[int] = Field(default=None, foreign_key="userprofile.id")  # Who created the job

    workspace: Optional["Workspace"] = Relationship(back_populates="jobs")

class Workspace(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    memberships: List["WorkspaceMembership"] = Relationship(back_populates="workspace")
    jobs: List["Job"] = Relationship(back_populates="workspace")
    portfolios: List["Portfolio"] = Relationship(back_populates="workspace", cascade_delete=True)
    strategies: List["Strategy"] = Relationship(back_populates="workspace", cascade_delete=True)

class WorkspaceMembership(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    role: str = Field(default="viewer")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    workspace_id: int = Field(foreign_key="workspace.id")
    user_profile_id: int = Field(foreign_key="userprofile.id")

    workspace: Optional[Workspace] = Relationship(back_populates="memberships")
    user_profile: Optional["UserProfile"] = Relationship(back_populates="workspace_memberships")

class Portfolio(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    initial_cash: Decimal = Field(sa_column=Column(DECIMAL(15, 2)), default=Decimal("0.00"))
    current_cash: Decimal = Field(sa_column=Column(DECIMAL(15, 2)), default=Decimal("0.00"))
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    workspace_id: int = Field(foreign_key="workspace.id")
    created_by: int = Field(foreign_key="userprofile.id")

    workspace: Optional[Workspace] = Relationship(back_populates="portfolios")
    created_by_user: Optional["UserProfile"] = Relationship()
    positions: List["Position"] = Relationship(back_populates="portfolio", cascade_delete=True)

    __table_args__ = (UniqueConstraint("workspace_id", "name"),)

class Position(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str = Field(index=True)
    quantity: Decimal = Field(sa_column=Column(DECIMAL(15, 8)))
    average_price: Decimal = Field(sa_column=Column(DECIMAL(15, 4)))
    current_price: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(15, 4)))
    position_type: str = Field(default="long")  # long, short
    opened_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    portfolio_id: int = Field(foreign_key="portfolio.id")

    portfolio: Optional[Portfolio] = Relationship(back_populates="positions")
    transactions: List["Transaction"] = Relationship(back_populates="position", cascade_delete=True)

class Transaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    transaction_type: str  # buy, sell, dividend, split, fee
    symbol: str = Field(index=True)
    quantity: Decimal = Field(sa_column=Column(DECIMAL(15, 8)))
    price: Decimal = Field(sa_column=Column(DECIMAL(15, 4)))
    total_amount: Decimal = Field(sa_column=Column(DECIMAL(15, 2)))
    fees: Decimal = Field(sa_column=Column(DECIMAL(10, 2)), default=Decimal("0.00"))
    notes: Optional[str] = Field(default=None, sa_column=Column(Text))
    executed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    portfolio_id: int = Field(foreign_key="portfolio.id")
    position_id: Optional[int] = Field(default=None, foreign_key="position.id")
    created_by: int = Field(foreign_key="userprofile.id")

    portfolio: Optional[Portfolio] = Relationship()
    position: Optional[Position] = Relationship(back_populates="transactions")
    created_by_user: Optional["UserProfile"] = Relationship()

class Strategy(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    strategy_type: str  # momentum, mean_reversion, arbitrage, custom
    strategy_code: Optional[str] = Field(default=None, sa_column=Column(Text))  # Python code for custom strategies
    is_active: bool = Field(default=True)
    is_public: bool = Field(default=False)  # Whether strategy can be shared/copied
    risk_level: str = Field(default="medium")  # low, medium, high
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    workspace_id: int = Field(foreign_key="workspace.id")
    created_by: int = Field(foreign_key="userprofile.id")

    workspace: Optional[Workspace] = Relationship()
    created_by_user: Optional["UserProfile"] = Relationship()
    parameters: List["StrategyParameter"] = Relationship(back_populates="strategy", cascade_delete=True)
    signals: List["Signal"] = Relationship(back_populates="strategy", cascade_delete=True)
    performance_records: List["StrategyPerformance"] = Relationship(back_populates="strategy", cascade_delete=True)

    __table_args__ = (UniqueConstraint("workspace_id", "name"),)

class StrategyParameter(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    parameter_name: str = Field(index=True)
    parameter_type: str  # int, float, string, boolean
    default_value: str  # Stored as string, converted based on type
    current_value: str  # Current parameter value
    min_value: Optional[str] = Field(default=None)  # For numeric parameters
    max_value: Optional[str] = Field(default=None)  # For numeric parameters
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    is_required: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    strategy_id: int = Field(foreign_key="strategy.id")

    strategy: Optional[Strategy] = Relationship(back_populates="parameters")

class Signal(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    signal_type: str  # buy, sell, hold
    symbol: str = Field(index=True)
    signal_strength: Decimal = Field(sa_column=Column(DECIMAL(5, 4)), default=Decimal("1.0000"))  # 0.0 to 1.0
    price: Decimal = Field(sa_column=Column(DECIMAL(15, 4)))
    quantity: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(15, 8)))
    confidence_score: Decimal = Field(sa_column=Column(DECIMAL(5, 4)), default=Decimal("0.5000"))  # 0.0 to 1.0
    signal_data: Optional[dict] = Field(default=None, sa_column=Column(JSON))  # Additional signal metadata
    is_executed: bool = Field(default=False)
    executed_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    strategy_id: int = Field(foreign_key="strategy.id")

    strategy: Optional[Strategy] = Relationship(back_populates="signals")

class StrategyPerformance(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    period_start: datetime = Field(index=True)
    period_end: datetime = Field(index=True)
    total_return: Decimal = Field(sa_column=Column(DECIMAL(15, 4)), default=Decimal("0.0000"))
    return_percentage: Decimal = Field(sa_column=Column(DECIMAL(8, 4)), default=Decimal("0.0000"))
    sharpe_ratio: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(8, 4)))
    max_drawdown: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(8, 4)))
    volatility: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(8, 4)))
    win_rate: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(5, 4)))  # 0.0 to 1.0
    total_trades: int = Field(default=0)
    winning_trades: int = Field(default=0)
    losing_trades: int = Field(default=0)
    avg_trade_return: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(8, 4)))
    performance_data: Optional[dict] = Field(default=None, sa_column=Column(JSON))  # Detailed metrics
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    strategy_id: int = Field(foreign_key="strategy.id")

    strategy: Optional[Strategy] = Relationship(back_populates="performance_records")


class Backtest(SQLModel, table=True):
    """Backtest configuration and metadata"""
    id: Optional[int] = Field(default=None, primary_key=True)
    backtest_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        sa_column=Column("backtest_id", String(36), unique=True, nullable=False)
    )
    name: str = Field(max_length=100, description="Backtest name")
    description: Optional[str] = Field(default=None, max_length=500)
    
    # Strategy and workspace references
    strategy_id: int = Field(foreign_key="strategy.id")
    workspace_id: int = Field(foreign_key="workspace.id")
    
    # Backtest configuration
    start_date: datetime = Field(description="Backtest start date")
    end_date: datetime = Field(description="Backtest end date")
    initial_capital: Decimal = Field(sa_column=Column(DECIMAL(15, 2)), description="Initial capital")
    symbols: Optional[List[str]] = Field(default=None, sa_column=Column(JSON), description="Symbols to backtest")
    
    # Execution settings
    commission_per_share: Decimal = Field(default=Decimal("0.01"), sa_column=Column(DECIMAL(8, 4)))
    commission_percentage: Decimal = Field(default=Decimal("0.0"), sa_column=Column(DECIMAL(5, 4)))
    slippage: Decimal = Field(default=Decimal("0.001"), sa_column=Column(DECIMAL(8, 4)))  # 0.1% default
    
    # Results summary
    status: str = Field(default="pending", description="pending, running, completed, failed")
    total_return: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(15, 2)))
    return_percentage: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(8, 4)))
    sharpe_ratio: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(8, 4)))
    max_drawdown: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(5, 4)))
    volatility: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(8, 4)))
    total_trades: int = Field(default=0)
    win_rate: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(5, 4)))
    
    # Metadata
    backtest_config: Optional[dict] = Field(default=None, sa_column=Column(JSON))  # Additional config
    error_message: Optional[str] = Field(default=None, sa_column=Column(Text))
    job_id: Optional[str] = Field(default=None, description="Associated job ID")
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    
    # User who created the backtest
    created_by: int = Field(foreign_key="userprofile.id")
    
    # Relationships
    strategy: Optional[Strategy] = Relationship()
    workspace: Optional[Workspace] = Relationship()
    trades: List["BacktestTrade"] = Relationship(back_populates="backtest")
    daily_metrics: List["BacktestDailyMetric"] = Relationship(back_populates="backtest")


class BacktestTrade(SQLModel, table=True):
    """Individual trades executed during backtest"""
    id: Optional[int] = Field(default=None, primary_key=True)
    backtest_id: int = Field(foreign_key="backtest.id")
    
    # Trade details
    symbol: str = Field(max_length=10)
    trade_type: str = Field(description="buy, sell, short, cover")
    quantity: int = Field(description="Number of shares")
    price: Decimal = Field(sa_column=Column(DECIMAL(12, 4)), description="Execution price")
    commission: Decimal = Field(default=Decimal("0"), sa_column=Column(DECIMAL(8, 4)))
    slippage: Decimal = Field(default=Decimal("0"), sa_column=Column(DECIMAL(8, 4)))
    
    # Trade timing
    signal_timestamp: datetime = Field(description="When signal was generated")
    execution_timestamp: datetime = Field(description="When trade was executed")
    
    # Portfolio context
    portfolio_value: Decimal = Field(sa_column=Column(DECIMAL(15, 2)), description="Portfolio value before trade")
    cash_balance: Decimal = Field(sa_column=Column(DECIMAL(15, 2)), description="Cash balance after trade")
    position_size: int = Field(description="Total position size after trade")
    
    # Trade metadata
    signal_strength: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(5, 4)))
    confidence_score: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(5, 4)))
    trade_data: Optional[dict] = Field(default=None, sa_column=Column(JSON))  # Additional trade info
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    
    # Relationships
    backtest: Optional[Backtest] = Relationship(back_populates="trades")


class BacktestDailyMetric(SQLModel, table=True):
    """Daily performance metrics during backtest"""
    id: Optional[int] = Field(default=None, primary_key=True)
    backtest_id: int = Field(foreign_key="backtest.id")
    
    # Date and basic metrics
    date: datetime = Field(description="Date of metrics")
    portfolio_value: Decimal = Field(sa_column=Column(DECIMAL(15, 2)))
    cash_balance: Decimal = Field(sa_column=Column(DECIMAL(15, 2)))
    positions_value: Decimal = Field(sa_column=Column(DECIMAL(15, 2)))
    total_equity: Decimal = Field(sa_column=Column(DECIMAL(15, 2)))
    
    # Performance metrics
    daily_return: Decimal = Field(sa_column=Column(DECIMAL(8, 6)))  # Daily return percentage
    daily_pnl: Decimal = Field(sa_column=Column(DECIMAL(12, 2)))  # Daily P&L amount
    cumulative_return: Decimal = Field(sa_column=Column(DECIMAL(8, 4)))  # Cumulative return %
    drawdown: Decimal = Field(sa_column=Column(DECIMAL(5, 4)))  # Current drawdown from peak
    
    # Risk metrics
    volatility: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(8, 4)))
    sharpe_ratio: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(8, 4)))
    
    # Trade activity
    trades_executed: int = Field(default=0, description="Number of trades executed this day")
    positions_count: int = Field(default=0, description="Number of open positions")
    
    # Additional metrics
    daily_metrics: Optional[dict] = Field(default=None, sa_column=Column(JSON))  # Extra daily metrics
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    
    # Relationships
    backtest: Optional[Backtest] = Relationship(back_populates="daily_metrics")


class BacktestPosition(SQLModel, table=True):
    """Current positions during backtest (snapshot)"""
    id: Optional[int] = Field(default=None, primary_key=True)
    backtest_id: int = Field(foreign_key="backtest.id")
    
    # Position details
    symbol: str = Field(max_length=10)
    quantity: int = Field(description="Number of shares (negative for short)")
    avg_price: Decimal = Field(sa_column=Column(DECIMAL(12, 4)), description="Average entry price")
    current_price: Decimal = Field(sa_column=Column(DECIMAL(12, 4)), description="Current market price")
    market_value: Decimal = Field(sa_column=Column(DECIMAL(15, 2)), description="Current market value")
    
    # Position P&L
    unrealized_pnl: Decimal = Field(sa_column=Column(DECIMAL(12, 2)))
    realized_pnl: Decimal = Field(sa_column=Column(DECIMAL(12, 2)), default=Decimal("0"))
    total_pnl: Decimal = Field(sa_column=Column(DECIMAL(12, 2)))
    
    # Position timing
    first_entry: datetime = Field(description="When position was first established")
    last_update: datetime = Field(description="When position was last modified")
    
    # Position metadata
    position_data: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    
    # Relationships
    backtest: Optional[Backtest] = Relationship()