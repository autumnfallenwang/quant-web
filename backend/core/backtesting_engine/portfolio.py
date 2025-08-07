# core/backtesting_engine/portfolio.py
"""
Portfolio simulation for backtesting - mirrors real Portfolio Engine behavior
This is a SIMULATION that behaves exactly like the real Portfolio Engine,
just with virtual money and historical data instead of real money and live data.
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class SimulationPosition:
    """
    Simulation version of real Position model
    Mirrors: models.db_models.Position
    """
    symbol: str
    quantity: Decimal  # Matches real Position.quantity (DECIMAL(15, 8))
    average_price: Decimal  # Matches real Position.average_price (DECIMAL(15, 4))
    current_price: Optional[Decimal] = None  # Matches real Position.current_price
    position_type: str = "long"  # Matches real Position.position_type (long, short)
    opened_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.opened_at is None:
            self.opened_at = datetime.now(timezone.utc)
        if self.updated_at is None:
            self.updated_at = datetime.now(timezone.utc)
    
    @property
    def market_value(self) -> Decimal:
        """Current market value - same calculation as real Portfolio"""
        if self.current_price is None:
            return Decimal("0")
        return self.quantity * self.current_price
    
    @property
    def unrealized_pnl(self) -> Decimal:
        """Unrealized P&L - same calculation as real Portfolio"""
        if self.current_price is None:
            return Decimal("0")
        return (self.current_price - self.average_price) * self.quantity
    
    @property
    def cost_basis(self) -> Decimal:
        """Original cost basis"""
        return self.average_price * abs(self.quantity)


@dataclass 
class SimulationTransaction:
    """
    Simulation version of real Transaction model
    Mirrors: models.db_models.Transaction
    """
    transaction_type: str  # buy, sell, dividend, split, fee - matches real Transaction
    symbol: str
    quantity: Decimal  # Matches real Transaction.quantity (DECIMAL(15, 8))
    price: Decimal  # Matches real Transaction.price (DECIMAL(15, 4))
    total_amount: Decimal  # Matches real Transaction.total_amount (DECIMAL(15, 2))
    fees: Decimal = Decimal("0.00")  # Matches real Transaction.fees (DECIMAL(10, 2))
    notes: Optional[str] = None
    executed_at: datetime = None
    created_at: datetime = None
    
    # Backtesting specific fields
    signal_strength: Optional[Decimal] = None
    confidence_score: Optional[Decimal] = None
    
    def __post_init__(self):
        if self.executed_at is None:
            self.executed_at = datetime.now(timezone.utc)
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)


class SimulationPortfolio:
    """
    Portfolio simulation that behaves EXACTLY like the real Portfolio Engine
    Mirrors: models.db_models.Portfolio + services.portfolio_service logic
    
    This is virtual money, but same calculations and behavior as real portfolio
    """
    
    def __init__(self, initial_cash: Decimal, name: str = "Backtest Portfolio"):
        # Mirror real Portfolio fields
        self.name = name
        self.description = "Backtesting simulation portfolio"
        self.initial_cash = initial_cash  # Matches real Portfolio.initial_cash
        self.current_cash = initial_cash  # Matches real Portfolio.current_cash
        self.is_active = True  # Matches real Portfolio.is_active
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        
        # Portfolio state - mirrors real Portfolio structure
        self.positions: Dict[str, SimulationPosition] = {}  # Like real Portfolio.positions
        self.transactions: List[SimulationTransaction] = []  # Like real Portfolio transactions
        
        # Performance tracking (for backtesting metrics)
        self.daily_snapshots: List[Dict] = []
        self.peak_value = initial_cash
    
    @property
    def total_value(self) -> Decimal:
        """
        Total portfolio value - SAME calculation as real Portfolio Engine
        cash + positions_value = total portfolio value
        """
        positions_value = sum(pos.market_value for pos in self.positions.values())
        return self.current_cash + positions_value
    
    @property
    def positions_value(self) -> Decimal:
        """Total value of all positions - same as real Portfolio"""
        return sum(pos.market_value for pos in self.positions.values())
    
    @property
    def unrealized_pnl(self) -> Decimal:
        """Total unrealized P&L - same calculation as real Portfolio"""
        return sum(pos.unrealized_pnl for pos in self.positions.values())
    
    @property
    def realized_pnl(self) -> Decimal:
        """Total realized P&L from closed positions"""
        return self.total_value - self.initial_cash - self.unrealized_pnl
    
    def execute_transaction(self, transaction: SimulationTransaction) -> bool:
        """
        Execute a transaction - mirrors real Portfolio Engine transaction processing
        Returns True if successful, False if not enough cash/shares
        """
        try:
            # Validate transaction based on type - same logic as real Portfolio
            if transaction.transaction_type == "buy":
                if not self._can_afford_purchase(transaction.total_amount + transaction.fees):
                    return False
                self._process_buy_transaction(transaction)
                
            elif transaction.transaction_type == "sell":
                if not self._can_sell_quantity(transaction.symbol, transaction.quantity):
                    return False
                self._process_sell_transaction(transaction)
                
            else:
                # Handle other transaction types (dividend, split, fee) same as real Portfolio
                self._process_other_transaction(transaction)
            
            # Add to transaction history
            self.transactions.append(transaction)
            self.updated_at = datetime.now(timezone.utc)
            
            return True
            
        except Exception as e:
            print(f"Error executing transaction: {e}")
            return False
    
    def _can_afford_purchase(self, total_cost: Decimal) -> bool:
        """Check if we have enough cash - same logic as real Portfolio"""
        return self.current_cash >= total_cost
    
    def _can_sell_quantity(self, symbol: str, quantity: Decimal) -> bool:
        """Check if we have enough shares to sell - same logic as real Portfolio"""
        if symbol not in self.positions:
            return False
        return self.positions[symbol].quantity >= quantity
    
    def _process_buy_transaction(self, transaction: SimulationTransaction):
        """Process buy transaction - same logic as real Portfolio Engine"""
        # Deduct cash
        total_cost = transaction.total_amount + transaction.fees
        self.current_cash -= total_cost
        
        # Add to position (or create new position)
        if transaction.symbol in self.positions:
            # Update existing position - weighted average price calculation (same as real)
            existing_pos = self.positions[transaction.symbol]
            
            total_quantity = existing_pos.quantity + transaction.quantity
            total_cost_basis = (existing_pos.average_price * existing_pos.quantity + 
                              transaction.price * transaction.quantity)
            new_avg_price = total_cost_basis / total_quantity
            
            existing_pos.quantity = total_quantity
            existing_pos.average_price = new_avg_price
            existing_pos.updated_at = transaction.executed_at
            
        else:
            # Create new position
            self.positions[transaction.symbol] = SimulationPosition(
                symbol=transaction.symbol,
                quantity=transaction.quantity,
                average_price=transaction.price,
                current_price=transaction.price,
                opened_at=transaction.executed_at,
                updated_at=transaction.executed_at
            )
    
    def _process_sell_transaction(self, transaction: SimulationTransaction):
        """Process sell transaction - same logic as real Portfolio Engine"""
        # Add cash from sale
        net_proceeds = transaction.total_amount - transaction.fees
        self.current_cash += net_proceeds
        
        # Reduce position
        position = self.positions[transaction.symbol]
        position.quantity -= transaction.quantity
        position.updated_at = transaction.executed_at
        
        # Remove position if quantity becomes zero
        if position.quantity <= Decimal("0"):
            del self.positions[transaction.symbol]
    
    def _process_other_transaction(self, transaction: SimulationTransaction):
        """Handle dividends, splits, fees - same as real Portfolio"""
        if transaction.transaction_type == "dividend":
            self.current_cash += transaction.total_amount
        elif transaction.transaction_type == "fee":
            self.current_cash -= transaction.total_amount
        # Add more transaction types as needed
    
    def update_market_prices(self, market_data: Dict[str, Decimal]):
        """
        Update current prices for all positions - same as real Portfolio Engine
        market_data: {symbol: current_price}
        """
        for symbol, position in self.positions.items():
            if symbol in market_data:
                position.current_price = market_data[symbol]
                position.updated_at = datetime.now(timezone.utc)
        
        self.updated_at = datetime.now(timezone.utc)
    
    def get_position(self, symbol: str) -> Optional[SimulationPosition]:
        """Get position for symbol - same interface as real Portfolio"""
        return self.positions.get(symbol)
    
    def get_all_positions(self) -> List[SimulationPosition]:
        """Get all positions - same interface as real Portfolio"""
        return list(self.positions.values())
    
    def record_daily_snapshot(self, date: datetime, additional_data: Optional[Dict] = None):
        """Record daily portfolio state for performance tracking"""
        snapshot = {
            "date": date,
            "total_value": self.total_value,
            "current_cash": self.current_cash,
            "positions_value": self.positions_value,
            "unrealized_pnl": self.unrealized_pnl,
            "realized_pnl": self.realized_pnl,
            "position_count": len(self.positions),
            "total_return": self.total_value - self.initial_cash,
            "return_percentage": ((self.total_value / self.initial_cash) - 1) if self.initial_cash > 0 else Decimal("0")
        }
        
        if additional_data:
            snapshot.update(additional_data)
        
        self.daily_snapshots.append(snapshot)
        
        # Update peak value for drawdown calculation
        if self.total_value > self.peak_value:
            self.peak_value = self.total_value
    
    def get_current_drawdown(self) -> Decimal:
        """Calculate current drawdown from peak - same as real Portfolio metrics"""
        if self.peak_value == 0:
            return Decimal("0")
        return (self.peak_value - self.total_value) / self.peak_value
    
    def get_portfolio_summary(self) -> Dict:
        """
        Get portfolio summary - same format as real Portfolio Engine
        This mirrors the real portfolio_service.get_portfolio_summary() output
        """
        return {
            "name": self.name,
            "description": self.description,
            "initial_cash": self.initial_cash,
            "current_cash": self.current_cash,
            "total_value": self.total_value,
            "positions_value": self.positions_value,
            "total_return": self.total_value - self.initial_cash,
            "return_percentage": ((self.total_value / self.initial_cash) - 1) * 100 if self.initial_cash > 0 else Decimal("0"),
            "unrealized_pnl": self.unrealized_pnl,
            "realized_pnl": self.realized_pnl,
            "current_drawdown": self.get_current_drawdown(),
            "peak_value": self.peak_value,
            "position_count": len(self.positions),
            "transaction_count": len(self.transactions),
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    def create_transaction_from_signal(
        self, 
        signal: Dict, 
        market_price: Decimal,
        commission: Decimal = Decimal("0.01")
    ) -> SimulationTransaction:
        """
        Create transaction from trading signal - convenience method for backtesting
        This mirrors how real Portfolio Engine would process signals
        """
        signal_type = signal.get("signal_type", "hold")
        symbol = signal.get("symbol")
        quantity = Decimal(str(signal.get("quantity", 100)))
        
        # Calculate total amount including commissions (same as real Portfolio)
        total_amount = market_price * quantity
        
        return SimulationTransaction(
            transaction_type="buy" if signal_type == "buy" else "sell",
            symbol=symbol,
            quantity=quantity,
            price=market_price,
            total_amount=total_amount,
            fees=commission,
            signal_strength=signal.get("signal_strength"),
            confidence_score=signal.get("confidence_score"),
            notes=f"Generated from {signal_type} signal"
        )