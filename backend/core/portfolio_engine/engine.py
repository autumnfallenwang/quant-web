# core/portfolio_engine/engine.py
from decimal import Decimal
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from .calculations import PortfolioCalculations


class PortfolioEngine:
    """
    Core portfolio engine for managing portfolio calculations and operations.
    """
    
    def __init__(self):
        self.calculations = PortfolioCalculations()
    
    def analyze_portfolio(
        self,
        portfolio_data: Dict[str, Any],
        positions_data: List[Dict[str, Any]],
        current_prices: Dict[str, Decimal]
    ) -> Dict[str, Any]:
        """
        Comprehensive portfolio analysis.
        
        Args:
            portfolio_data: {'id': int, 'initial_cash': Decimal, 'current_cash': Decimal}
            positions_data: [{'symbol': str, 'quantity': Decimal, 'average_price': Decimal}, ...]
            current_prices: {'AAPL': Decimal('150.00'), 'MSFT': Decimal('300.00'), ...}
        
        Returns:
            Complete portfolio analysis including values, P&L, allocation, and risk metrics
        """
        # Enrich positions with current prices
        enriched_positions = []
        for pos in positions_data:
            symbol = pos['symbol']
            current_price = current_prices.get(symbol, pos.get('current_price', Decimal('0.00')))
            
            enriched_position = {
                'symbol': symbol,
                'quantity': pos['quantity'],
                'average_price': pos['average_price'],
                'current_price': current_price
            }
            enriched_positions.append(enriched_position)
        
        # Calculate portfolio metrics
        total_value = self.calculations.calculate_portfolio_value(
            portfolio_data['current_cash'], enriched_positions
        )
        
        allocation = self.calculations.calculate_portfolio_allocation(
            portfolio_data['current_cash'], enriched_positions
        )
        
        risk_metrics = self.calculations.calculate_risk_metrics(enriched_positions)
        
        # Calculate overall P&L
        absolute_return, percentage_return = self.calculations.calculate_portfolio_returns(
            total_value, portfolio_data['initial_cash']
        )
        
        # Calculate position details
        position_details = []
        for pos in enriched_positions:
            position_value = self.calculations.calculate_position_value(
                pos['quantity'], pos['current_price']
            )
            unrealized_pnl, unrealized_pnl_percent = self.calculations.calculate_position_pnl(
                pos['quantity'], pos['average_price'], pos['current_price']
            )
            
            position_details.append({
                'symbol': pos['symbol'],
                'quantity': pos['quantity'],
                'average_price': pos['average_price'],
                'current_price': pos['current_price'],
                'market_value': position_value,
                'unrealized_pnl': unrealized_pnl,
                'unrealized_pnl_percent': unrealized_pnl_percent,
                'allocation_percent': allocation.get(pos['symbol'], Decimal('0.00'))
            })
        
        return {
            'portfolio_id': portfolio_data['id'],
            'summary': {
                'total_value': total_value,
                'cash': portfolio_data['current_cash'],
                'positions_value': total_value - portfolio_data['current_cash'],
                'absolute_return': absolute_return,
                'percentage_return': percentage_return,
                'position_count': len(enriched_positions)
            },
            'allocation': allocation,
            'risk_metrics': risk_metrics,
            'positions': position_details,
            'analysis_timestamp': datetime.now(timezone.utc)
        }
    
    def simulate_trade(
        self,
        current_position: Optional[Dict[str, Decimal]],
        trade_quantity: Decimal,
        trade_price: Decimal,
        trade_type: str = "buy"
    ) -> Dict[str, Any]:
        """
        Simulate a trade without executing it.
        
        Args:
            current_position: {'quantity': Decimal, 'average_price': Decimal} or None
            trade_quantity: Quantity to trade (positive)
            trade_price: Price per share
            trade_type: 'buy' or 'sell'
        
        Returns:
            Simulated position after trade
        """
        if not current_position:
            current_position = {'quantity': Decimal('0'), 'average_price': Decimal('0')}
        
        current_qty = current_position['quantity']
        current_avg = current_position['average_price']
        
        if trade_type == "buy":
            new_quantity = current_qty + trade_quantity
            new_avg_price = self.calculations.calculate_weighted_average_price(
                current_qty, current_avg, trade_quantity, trade_price
            )
        elif trade_type == "sell":
            if trade_quantity > current_qty:
                raise ValueError(f"Cannot sell {trade_quantity} shares, only {current_qty} available")
            
            new_quantity = current_qty - trade_quantity
            new_avg_price = current_avg  # Average price doesn't change on sell
        else:
            raise ValueError(f"Invalid trade_type: {trade_type}")
        
        trade_value = trade_quantity * trade_price
        
        return {
            'new_quantity': new_quantity,
            'new_average_price': new_avg_price,
            'trade_value': trade_value,
            'trade_type': trade_type,
            'trade_quantity': trade_quantity,
            'trade_price': trade_price
        }
    
    def calculate_required_cash(
        self,
        trades: List[Dict[str, Any]]
    ) -> Decimal:
        """
        Calculate total cash required for a list of buy trades.
        
        Args:
            trades: [{'trade_type': str, 'quantity': Decimal, 'price': Decimal, 'fees': Decimal}, ...]
        """
        total_cash_needed = Decimal('0.00')
        
        for trade in trades:
            if trade['trade_type'] == 'buy':
                trade_value = trade['quantity'] * trade['price']
                fees = trade.get('fees', Decimal('0.00'))
                total_cash_needed += trade_value + fees
        
        return total_cash_needed.quantize(Decimal('0.01'))
    
    def validate_portfolio_state(
        self,
        cash: Decimal,
        positions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate portfolio state for consistency.
        
        Returns validation results and any issues found.
        """
        issues = []
        warnings = []
        
        # Check for negative cash
        if cash < 0:
            issues.append(f"Portfolio has negative cash: {cash}")
        
        # Check for negative positions
        for pos in positions:
            if pos['quantity'] < 0:
                issues.append(f"Position {pos['symbol']} has negative quantity: {pos['quantity']}")
            
            if pos['average_price'] < 0:
                issues.append(f"Position {pos['symbol']} has negative average price: {pos['average_price']}")
        
        # Check for high concentration risk
        risk_metrics = self.calculations.calculate_risk_metrics(positions)
        if risk_metrics['concentration_risk'] > 50:
            warnings.append(f"High concentration risk: {risk_metrics['concentration_risk']}% in single position")
        
        return {
            'is_valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'risk_metrics': risk_metrics
        }