# core/backtesting_engine/execution.py
"""
Execution engine for backtesting - handles order processing and trade execution
"""
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List, Dict, Optional, Any
from enum import Enum
from dataclasses import dataclass

from .portfolio import SimulationPortfolio, SimulationTransaction


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Order:
    """Represents a trading order during backtesting"""
    symbol: str
    order_type: OrderType
    side: str  # buy, sell
    quantity: Decimal
    price: Optional[Decimal] = None  # For limit orders
    stop_price: Optional[Decimal] = None  # For stop orders
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = None
    filled_at: Optional[datetime] = None
    filled_quantity: Decimal = Decimal("0")
    filled_price: Optional[Decimal] = None
    commission: Decimal = Decimal("0")
    order_id: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.order_id is None:
            self.order_id = f"ord_{int(self.created_at.timestamp())}"


class ExecutionEngine:
    """
    Handles order execution during backtesting with realistic market mechanics
    """
    
    def __init__(self, config):
        self.config = config
        self.pending_orders: List[Order] = []
        self.executed_orders: List[Order] = []
        
    async def execute_signals(
        self,
        signals: List[Dict[str, Any]],
        portfolio: SimulationPortfolio,
        market_data: Dict[str, Dict[str, Any]]
    ) -> List[SimulationTransaction]:
        """
        Execute trading signals and return completed transactions
        """
        executed_transactions = []
        
        for signal in signals:
            # Convert signal to order
            order = self._signal_to_order(signal)
            
            # Execute order immediately (market order simulation)
            if order.order_type == OrderType.MARKET:
                transaction = await self._execute_market_order(order, market_data, portfolio)
                if transaction and portfolio.execute_transaction(transaction):
                    executed_transactions.append(transaction)
                    order.status = OrderStatus.FILLED
                    order.filled_at = datetime.now(timezone.utc)
                    self.executed_orders.append(order)
                else:
                    order.status = OrderStatus.REJECTED
            else:
                # Add to pending orders for limit/stop orders
                self.pending_orders.append(order)
        
        # Process pending orders
        pending_transactions = await self._process_pending_orders(market_data, portfolio)
        executed_transactions.extend(pending_transactions)
        
        return executed_transactions
    
    def _signal_to_order(self, signal: Dict[str, Any]) -> Order:
        """Convert trading signal to executable order"""
        signal_type = signal.get("signal_type", "hold")
        
        if signal_type in ["buy", "sell"]:
            return Order(
                symbol=signal.get("symbol"),
                order_type=OrderType.MARKET,  # Default to market orders for simplicity
                side=signal_type,
                quantity=Decimal(str(signal.get("quantity", 100))),
                price=signal.get("price"),  # Reference price from signal
                created_at=signal.get("generated_at", datetime.now(timezone.utc))
            )
        
        return None
    
    async def _execute_market_order(
        self,
        order: Order,
        market_data: Dict[str, Dict[str, Any]],
        portfolio: SimulationPortfolio
    ) -> Optional[SimulationTransaction]:
        """Execute market order with realistic slippage and delays"""
        
        if order.symbol not in market_data or market_data[order.symbol] is None:
            return None  # No market data available
        
        symbol_data = market_data[order.symbol]
        
        # Calculate execution price with slippage
        base_price = symbol_data["close"]
        execution_price = self._apply_slippage(base_price, order.side, order.quantity)
        
        # Calculate commission
        commission = self._calculate_commission(order.quantity, execution_price)
        
        # Apply execution delay (simulate realistic order processing)
        execution_time = order.created_at + timedelta(minutes=self.config.execution_delay)
        
        # Calculate total amount
        total_amount = execution_price * order.quantity
        
        # Create transaction
        transaction = SimulationTransaction(
            transaction_type=order.side,
            symbol=order.symbol,
            quantity=order.quantity,
            price=execution_price,
            total_amount=total_amount,
            fees=commission,
            executed_at=execution_time,
            created_at=order.created_at,
            notes=f"Market order execution"
        )
        
        # Update order details
        order.filled_price = execution_price
        order.filled_quantity = order.quantity
        order.commission = commission
        
        return transaction
    
    def _apply_slippage(self, base_price: Decimal, side: str, quantity: Decimal) -> Decimal:
        """Apply slippage based on order size and market impact"""
        
        # Base slippage from config
        slippage_rate = self.config.slippage
        
        # Additional market impact based on order size
        market_impact = self.config.market_impact * (quantity / Decimal("1000"))  # Per 1000 shares
        
        total_slippage = slippage_rate + market_impact
        
        # Apply slippage (buy orders pay more, sell orders receive less)
        if side == "buy":
            return base_price * (Decimal("1") + total_slippage)
        else:  # sell
            return base_price * (Decimal("1") - total_slippage)
    
    def _calculate_commission(self, quantity: Decimal, price: Decimal) -> Decimal:
        """Calculate commission based on config settings"""
        per_share_commission = self.config.commission_per_share * quantity
        percentage_commission = price * quantity * self.config.commission_percentage
        
        return per_share_commission + percentage_commission
    
    async def _process_pending_orders(
        self,
        market_data: Dict[str, Dict[str, Any]],
        portfolio: SimulationPortfolio
    ) -> List[SimulationTransaction]:
        """Process pending limit and stop orders"""
        executed_transactions = []
        orders_to_remove = []
        
        for order in self.pending_orders:
            if order.symbol not in market_data or market_data[order.symbol] is None:
                continue
            
            symbol_data = market_data[order.symbol]
            current_price = symbol_data["close"]
            high_price = symbol_data["high"]
            low_price = symbol_data["low"]
            
            should_execute = False
            execution_price = current_price
            
            # Check execution conditions based on order type
            if order.order_type == OrderType.LIMIT:
                if order.side == "buy" and low_price <= order.price:
                    should_execute = True
                    execution_price = min(order.price, current_price)
                elif order.side == "sell" and high_price >= order.price:
                    should_execute = True
                    execution_price = max(order.price, current_price)
            
            elif order.order_type == OrderType.STOP:
                if order.side == "buy" and high_price >= order.stop_price:
                    should_execute = True
                    execution_price = max(order.stop_price, current_price)
                elif order.side == "sell" and low_price <= order.stop_price:
                    should_execute = True
                    execution_price = min(order.stop_price, current_price)
            
            if should_execute:
                # Create and execute transaction
                commission = self._calculate_commission(order.quantity, execution_price)
                total_amount = execution_price * order.quantity
                
                transaction = SimulationTransaction(
                    transaction_type=order.side,
                    symbol=order.symbol,
                    quantity=order.quantity,
                    price=execution_price,
                    total_amount=total_amount,
                    fees=commission,
                    executed_at=datetime.now(timezone.utc),
                    created_at=order.created_at,
                    notes=f"{order.order_type.value} order execution"
                )
                
                if portfolio.execute_transaction(transaction):
                    executed_transactions.append(transaction)
                    order.status = OrderStatus.FILLED
                    order.filled_at = datetime.now(timezone.utc)
                    order.filled_price = execution_price
                    order.filled_quantity = order.quantity
                    order.commission = commission
                    self.executed_orders.append(order)
                    orders_to_remove.append(order)
        
        # Remove executed orders from pending
        for order in orders_to_remove:
            self.pending_orders.remove(order)
        
        return executed_transactions
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get summary of execution statistics"""
        total_orders = len(self.executed_orders) + len(self.pending_orders)
        filled_orders = len(self.executed_orders)
        
        total_commission = sum(order.commission for order in self.executed_orders)
        
        return {
            "total_orders": total_orders,
            "filled_orders": filled_orders,
            "pending_orders": len(self.pending_orders),
            "fill_rate": filled_orders / total_orders if total_orders > 0 else 0,
            "total_commission": total_commission,
            "avg_commission_per_trade": total_commission / filled_orders if filled_orders > 0 else Decimal("0")
        }