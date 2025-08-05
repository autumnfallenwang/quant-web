# core/portfolio_engine/calculations.py
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Tuple


class PortfolioCalculations:
    
    @staticmethod
    def calculate_position_value(quantity: Decimal, current_price: Decimal) -> Decimal:
        """Calculate current market value of a position."""
        return (quantity * current_price).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calculate_position_pnl(
        quantity: Decimal, 
        average_price: Decimal, 
        current_price: Decimal
    ) -> Tuple[Decimal, Decimal]:
        """
        Calculate position P&L.
        Returns: (unrealized_pnl, unrealized_pnl_percent)
        """
        cost_basis = quantity * average_price
        current_value = quantity * current_price
        
        unrealized_pnl = (current_value - cost_basis).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        if cost_basis > 0:
            unrealized_pnl_percent = ((current_value / cost_basis - 1) * 100).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
        else:
            unrealized_pnl_percent = Decimal('0.00')
            
        return unrealized_pnl, unrealized_pnl_percent
    
    @staticmethod
    def calculate_portfolio_value(
        cash: Decimal,
        positions: List[Dict[str, Decimal]]
    ) -> Decimal:
        """
        Calculate total portfolio value.
        positions format: [{'quantity': Decimal, 'current_price': Decimal}, ...]
        """
        positions_value = sum(
            PortfolioCalculations.calculate_position_value(pos['quantity'], pos['current_price'])
            for pos in positions
        )
        return (cash + positions_value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calculate_portfolio_allocation(
        cash: Decimal,
        positions: List[Dict[str, any]]
    ) -> Dict[str, Decimal]:
        """
        Calculate portfolio allocation percentages.
        positions format: [{'symbol': str, 'quantity': Decimal, 'current_price': Decimal}, ...]
        Returns: {'CASH': percent, 'AAPL': percent, ...}
        """
        total_value = PortfolioCalculations.calculate_portfolio_value(cash, positions)
        
        if total_value <= 0:
            return {'CASH': Decimal('100.00')}
        
        allocation = {}
        
        # Cash allocation
        cash_percent = (cash / total_value * 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        allocation['CASH'] = cash_percent
        
        # Position allocations
        for pos in positions:
            position_value = PortfolioCalculations.calculate_position_value(
                pos['quantity'], pos['current_price']
            )
            position_percent = (position_value / total_value * 100).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
            allocation[pos['symbol']] = position_percent
            
        return allocation
    
    @staticmethod
    def calculate_weighted_average_price(
        current_quantity: Decimal,
        current_avg_price: Decimal,
        new_quantity: Decimal,
        new_price: Decimal
    ) -> Decimal:
        """Calculate new weighted average price after adding position."""
        if current_quantity <= 0:
            return new_price
            
        total_cost = (current_quantity * current_avg_price) + (new_quantity * new_price)
        total_quantity = current_quantity + new_quantity
        
        if total_quantity <= 0:
            return Decimal('0.00')
            
        return (total_cost / total_quantity).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calculate_portfolio_returns(
        current_value: Decimal,
        initial_value: Decimal,
        cash_flows: Decimal = Decimal('0.00')
    ) -> Tuple[Decimal, Decimal]:
        """
        Calculate portfolio returns.
        cash_flows: net deposits/withdrawals (positive for deposits)
        Returns: (absolute_return, percentage_return)
        """
        adjusted_initial = initial_value + cash_flows
        
        if adjusted_initial <= 0:
            return Decimal('0.00'), Decimal('0.00')
            
        absolute_return = (current_value - adjusted_initial).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        percentage_return = ((current_value / adjusted_initial - 1) * 100).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        
        return absolute_return, percentage_return
    
    @staticmethod
    def calculate_risk_metrics(positions: List[Dict[str, any]]) -> Dict[str, Decimal]:
        """
        Calculate basic risk metrics.
        positions format: [{'symbol': str, 'quantity': Decimal, 'current_price': Decimal}, ...]
        """
        if not positions:
            return {
                'concentration_risk': Decimal('0.00'),
                'largest_position': Decimal('0.00'),
                'position_count': 0
            }
        
        total_value = sum(
            PortfolioCalculations.calculate_position_value(pos['quantity'], pos['current_price'])
            for pos in positions
        )
        
        if total_value <= 0:
            return {
                'concentration_risk': Decimal('0.00'),
                'largest_position': Decimal('0.00'),
                'position_count': len(positions)
            }
        
        # Find largest position percentage
        largest_position_value = max(
            PortfolioCalculations.calculate_position_value(pos['quantity'], pos['current_price'])
            for pos in positions
        )
        largest_position_percent = (largest_position_value / total_value * 100).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        
        return {
            'concentration_risk': largest_position_percent,
            'largest_position': largest_position_percent,
            'position_count': len(positions)
        }