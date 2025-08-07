# core/strategy_engine/signal_generators.py
"""
Signal generators for different trading strategies
"""
import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Any

from models.db_models import StrategyParameter


class BaseSignalGenerator(ABC):
    """Base class for all signal generators"""
    
    def __init__(self, parameters: Dict[str, StrategyParameter]):
        self.parameters = parameters
    
    @abstractmethod
    async def generate_signals(self, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate trading signals based on market data"""
        pass
    
    def get_parameter_value(self, param_name: str, default_value: Any = None) -> Any:
        """Get parameter value with type conversion"""
        if param_name not in self.parameters:
            return default_value
        
        param = self.parameters[param_name]
        value = param.current_value
        
        try:
            if param.parameter_type == "int":
                return int(value)
            elif param.parameter_type == "float":
                return float(value)
            elif param.parameter_type == "boolean":
                return value.lower() in ["true", "1", "yes"]
            else:
                return value
        except (ValueError, TypeError):
            return default_value


class MomentumSignalGenerator(BaseSignalGenerator):
    """Signal generator for momentum-based strategies"""
    
    async def generate_signals(self, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate momentum signals"""
        signals = []
        
        # Get parameters with defaults
        lookback_period = self.get_parameter_value("lookback_period", 20)
        momentum_threshold = self.get_parameter_value("momentum_threshold", 0.05)
        min_volume = self.get_parameter_value("min_volume", 100000)
        
        # Process each symbol in market data
        for symbol, data in market_data.items():
            if not self._validate_market_data(data, lookback_period):
                continue
            
            # Calculate momentum indicators
            momentum_score = self._calculate_momentum(data, lookback_period)
            rsi = self._calculate_rsi(data, 14)
            volume_ratio = self._calculate_volume_ratio(data, lookback_period)
            
            # Generate signal based on momentum
            signal = self._generate_momentum_signal(
                symbol, data, momentum_score, rsi, volume_ratio, momentum_threshold, min_volume
            )
            
            if signal:
                signals.append(signal)
        
        return signals
    
    def _validate_market_data(self, data: Dict[str, Any], required_periods: int) -> bool:
        """Validate that we have enough data for analysis"""
        prices = data.get("prices", [])
        volumes = data.get("volumes", [])
        return len(prices) >= required_periods and len(volumes) >= required_periods
    
    def _calculate_momentum(self, data: Dict[str, Any], periods: int) -> Decimal:
        """Calculate price momentum over specified periods"""
        prices = data.get("prices", [])
        if len(prices) < periods:
            return Decimal("0.00")
        
        current_price = Decimal(str(prices[-1]))
        past_price = Decimal(str(prices[-periods]))
        
        momentum = ((current_price - past_price) / past_price * 100).quantize(Decimal('0.01'))
        return momentum
    
    def _calculate_rsi(self, data: Dict[str, Any], periods: int = 14) -> Decimal:
        """Calculate Relative Strength Index"""
        prices = data.get("prices", [])
        if len(prices) < periods + 1:
            return Decimal("50.00")  # Neutral RSI
        
        # Calculate price changes
        price_changes = []
        for i in range(1, len(prices)):
            change = Decimal(str(prices[i])) - Decimal(str(prices[i-1]))
            price_changes.append(change)
        
        # Separate gains and losses
        gains = [max(change, Decimal("0")) for change in price_changes[-periods:]]
        losses = [abs(min(change, Decimal("0"))) for change in price_changes[-periods:]]
        
        # Calculate average gain and loss
        avg_gain = sum(gains) / Decimal(str(periods)) if gains else Decimal("0")
        total_losses = sum(losses)
        avg_loss = total_losses / Decimal(str(periods)) if total_losses > 0 else Decimal("0")
        
        # Calculate RSI
        if avg_loss == Decimal("0"):  # No losses case
            if avg_gain > Decimal("0"):
                rsi = Decimal("100.00")
            else:
                rsi = Decimal("50.00")  # Neutral if no gains or losses
        else:
            rs = avg_gain / avg_loss
            rsi = (Decimal("100") - (Decimal("100") / (Decimal("1") + rs))).quantize(Decimal('0.01'))
        
        return rsi
    
    def _calculate_volume_ratio(self, data: Dict[str, Any], periods: int) -> Decimal:
        """Calculate current volume vs average volume"""
        volumes = data.get("volumes", [])
        if len(volumes) < periods:
            return Decimal("1.00")
        
        current_volume = Decimal(str(volumes[-1]))
        avg_volume = sum(Decimal(str(v)) for v in volumes[-periods:]) / Decimal(str(periods))
        
        ratio = (current_volume / avg_volume).quantize(Decimal('0.01')) if avg_volume > 0 else Decimal("1.00")
        return ratio
    
    def _generate_momentum_signal(
        self, 
        symbol: str, 
        data: Dict[str, Any], 
        momentum_score: Decimal, 
        rsi: Decimal, 
        volume_ratio: Decimal,
        momentum_threshold: float,
        min_volume: int
    ) -> Optional[Dict[str, Any]]:
        """Generate signal based on momentum analysis"""
        
        current_price = Decimal(str(data["prices"][-1]))
        current_volume = int(data["volumes"][-1])
        
        # Check minimum volume requirement
        if current_volume < min_volume:
            return None
        
        # Determine signal type and strength
        signal_type = "hold"
        signal_strength = Decimal("0.50")
        confidence_score = Decimal("0.50")
        
        momentum_threshold_decimal = Decimal(str(momentum_threshold))
        
        # Strong upward momentum
        if momentum_score > momentum_threshold_decimal and rsi < Decimal("70") and volume_ratio > Decimal("1.2"):
            signal_type = "buy"
            signal_strength = min(momentum_score / 10, Decimal("1.00"))
            confidence_score = Decimal("0.75")
        
        # Strong downward momentum
        elif momentum_score < -momentum_threshold_decimal and rsi > Decimal("30") and volume_ratio > Decimal("1.2"):
            signal_type = "sell"
            signal_strength = min(abs(momentum_score) / 10, Decimal("1.00"))
            confidence_score = Decimal("0.75")
        
        # Weak signals
        elif abs(momentum_score) > momentum_threshold_decimal / 2:
            if momentum_score > 0:
                signal_type = "buy"
            else:
                signal_type = "sell"
            signal_strength = Decimal("0.30")
            confidence_score = Decimal("0.50")
        
        return {
            "signal_type": signal_type,
            "symbol": symbol,
            "signal_strength": signal_strength,
            "price": current_price,
            "confidence_score": confidence_score,
            "signal_data": {
                "momentum_score": momentum_score,
                "rsi": rsi,
                "volume_ratio": volume_ratio,
                "current_volume": current_volume
            },
            "created_at": datetime.now(timezone.utc)
        }


class MeanReversionSignalGenerator(BaseSignalGenerator):
    """Signal generator for mean reversion strategies"""
    
    async def generate_signals(self, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate mean reversion signals"""
        signals = []
        
        # Get parameters
        bollinger_periods = self.get_parameter_value("bollinger_periods", 20)
        bollinger_std = self.get_parameter_value("bollinger_std", 2.0)
        oversold_threshold = self.get_parameter_value("oversold_threshold", 30)
        overbought_threshold = self.get_parameter_value("overbought_threshold", 70)
        
        for symbol, data in market_data.items():
            if not self._validate_market_data(data, bollinger_periods):
                continue
                
            # Calculate mean reversion indicators
            bollinger_bands = self._calculate_bollinger_bands(data, bollinger_periods, bollinger_std)
            rsi = self._calculate_rsi(data, 14)
            current_price = Decimal(str(data["prices"][-1]))
            
            # Generate signal
            signal = self._generate_mean_reversion_signal(
                symbol, current_price, bollinger_bands, rsi, 
                oversold_threshold, overbought_threshold
            )
            
            if signal:
                signals.append(signal)
        
        return signals
    
    def _validate_market_data(self, data: Dict[str, Any], required_periods: int) -> bool:
        """Validate market data"""
        prices = data.get("prices", [])
        return len(prices) >= required_periods
    
    def _calculate_bollinger_bands(self, data: Dict[str, Any], periods: int, std_dev: float) -> Dict[str, Decimal]:
        """Calculate Bollinger Bands"""
        prices = data.get("prices", [])[-periods:]
        prices_decimal = [Decimal(str(p)) for p in prices]
        
        # Calculate moving average
        sma = sum(prices_decimal) / len(prices_decimal)
        
        # Calculate standard deviation
        variance = sum((p - sma) ** Decimal('2') for p in prices_decimal) / len(prices_decimal)
        # Convert to float for square root, then back to Decimal
        std = Decimal(str(float(variance) ** 0.5))
        
        # Calculate bands
        upper_band = sma + (std * Decimal(str(std_dev)))
        lower_band = sma - (std * Decimal(str(std_dev)))
        
        return {
            "upper": upper_band,
            "middle": sma,
            "lower": lower_band
        }
    
    def _calculate_rsi(self, data: Dict[str, Any], periods: int = 14) -> Decimal:
        """Calculate RSI (reused from momentum generator)"""
        prices = data.get("prices", [])
        if len(prices) < periods + 1:
            return Decimal("50.00")
        
        price_changes = []
        for i in range(1, len(prices)):
            change = Decimal(str(prices[i])) - Decimal(str(prices[i-1]))
            price_changes.append(change)
        
        gains = [max(change, Decimal("0")) for change in price_changes[-periods:]]
        losses = [abs(min(change, Decimal("0"))) for change in price_changes[-periods:]]
        
        avg_gain = sum(gains) / Decimal(str(periods)) if gains else Decimal("0")
        total_losses = sum(losses)
        avg_loss = total_losses / Decimal(str(periods)) if total_losses > 0 else Decimal("0")
        
        # Calculate RSI
        if avg_loss == Decimal("0"):  # No losses case
            if avg_gain > Decimal("0"):
                rsi = Decimal("100.00")
            else:
                rsi = Decimal("50.00")  # Neutral if no gains or losses
        else:
            rs = avg_gain / avg_loss
            rsi = (Decimal("100") - (Decimal("100") / (Decimal("1") + rs))).quantize(Decimal('0.01'))
        
        return rsi
    
    def _generate_mean_reversion_signal(
        self,
        symbol: str,
        current_price: Decimal,
        bollinger_bands: Dict[str, Decimal],
        rsi: Decimal,
        oversold_threshold: float,
        overbought_threshold: float
    ) -> Optional[Dict[str, Any]]:
        """Generate mean reversion signal"""
        
        signal_type = "hold"
        signal_strength = Decimal("0.50")
        confidence_score = Decimal("0.50")
        
        # Price near lower Bollinger Band and RSI oversold = buy signal
        if (current_price <= bollinger_bands["lower"] and 
            rsi <= Decimal(str(oversold_threshold))):
            signal_type = "buy"
            signal_strength = Decimal("0.80")
            confidence_score = Decimal("0.75")
        
        # Price near upper Bollinger Band and RSI overbought = sell signal
        elif (current_price >= bollinger_bands["upper"] and 
              rsi >= Decimal(str(overbought_threshold))):
            signal_type = "sell"
            signal_strength = Decimal("0.80")
            confidence_score = Decimal("0.75")
        
        return {
            "signal_type": signal_type,
            "symbol": symbol,
            "signal_strength": signal_strength,
            "price": current_price,
            "confidence_score": confidence_score,
            "signal_data": {
                "bollinger_upper": bollinger_bands["upper"],
                "bollinger_middle": bollinger_bands["middle"],
                "bollinger_lower": bollinger_bands["lower"],
                "rsi": rsi
            },
            "created_at": datetime.now(timezone.utc)
        }


class ArbitrageSignalGenerator(BaseSignalGenerator):
    """Signal generator for arbitrage opportunities"""
    
    async def generate_signals(self, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate arbitrage signals"""
        signals = []
        
        # Get parameters
        min_spread = self.get_parameter_value("min_spread_percentage", 0.5)
        max_position_size = self.get_parameter_value("max_position_size", 10000)
        
        # Look for arbitrage opportunities between different symbols/exchanges
        # This is a simplified example - real arbitrage would need multiple data sources
        
        symbols = list(market_data.keys())
        for i, symbol1 in enumerate(symbols):
            for symbol2 in symbols[i+1:]:
                # Skip if same symbol
                if symbol1 == symbol2:
                    continue
                
                # Look for price discrepancies (simplified example)
                data1 = market_data[symbol1]
                data2 = market_data[symbol2]
                
                if self._are_related_assets(symbol1, symbol2):
                    signal = self._check_arbitrage_opportunity(
                        symbol1, data1, symbol2, data2, min_spread, max_position_size
                    )
                    if signal:
                        signals.append(signal)
        
        return signals
    
    def _are_related_assets(self, symbol1: str, symbol2: str) -> bool:
        """Check if two assets are related for arbitrage (simplified)"""
        # In reality, this would check for:
        # - Same asset on different exchanges
        # - Related ETFs and underlying assets
        # - Currency pairs
        # - Futures and spot prices
        
        # For demo, assume assets with similar names are related
        return symbol1[:2] == symbol2[:2]
    
    def _check_arbitrage_opportunity(
        self,
        symbol1: str, data1: Dict[str, Any],
        symbol2: str, data2: Dict[str, Any],
        min_spread: float, max_position_size: int
    ) -> Optional[Dict[str, Any]]:
        """Check for arbitrage opportunity between two assets"""
        
        price1 = Decimal(str(data1["prices"][-1]))
        price2 = Decimal(str(data2["prices"][-1]))
        
        # Calculate spread
        if price1 > price2:
            spread_percentage = ((price1 - price2) / price2 * 100).quantize(Decimal('0.01'))
            buy_symbol = symbol2
            sell_symbol = symbol1
            buy_price = price2
            sell_price = price1
        else:
            spread_percentage = ((price2 - price1) / price1 * 100).quantize(Decimal('0.01'))
            buy_symbol = symbol1
            sell_symbol = symbol2
            buy_price = price1
            sell_price = price2
        
        # Check if spread is large enough
        if spread_percentage < Decimal(str(min_spread)):
            return None
        
        # Calculate confidence based on spread size
        confidence_score = min(spread_percentage / 5, Decimal("0.95"))  # Higher spread = higher confidence
        
        return {
            "signal_type": "arbitrage",
            "symbol": f"{buy_symbol}/{sell_symbol}",
            "signal_strength": Decimal("0.90"),  # Arbitrage is typically high confidence
            "price": buy_price,
            "confidence_score": confidence_score,
            "signal_data": {
                "buy_symbol": buy_symbol,
                "sell_symbol": sell_symbol,
                "buy_price": buy_price,
                "sell_price": sell_price,
                "spread_percentage": spread_percentage,
                "max_position_size": max_position_size
            },
            "created_at": datetime.now(timezone.utc)
        }


class CustomSignalGenerator(BaseSignalGenerator):
    """Signal generator for custom strategy code"""
    
    def __init__(self, strategy_code: str, parameters: Dict[str, StrategyParameter]):
        super().__init__(parameters)
        self.strategy_code = strategy_code
    
    async def generate_signals(self, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute custom strategy code to generate signals"""
        
        # In production, this would need proper sandboxing and security measures
        # For now, return a placeholder implementation
        
        signals = []
        
        try:
            # This is where we would safely execute the custom strategy code
            # For security reasons, this is just a placeholder
            
            # Example: Parse simple custom rules from strategy code
            if "momentum" in self.strategy_code.lower():
                # Delegate to momentum generator
                momentum_gen = MomentumSignalGenerator(self.parameters)
                signals = await momentum_gen.generate_signals(market_data)
            
            elif "mean_reversion" in self.strategy_code.lower():
                # Delegate to mean reversion generator
                mean_rev_gen = MeanReversionSignalGenerator(self.parameters)
                signals = await mean_rev_gen.generate_signals(market_data)
            
            else:
                # Generate basic signals for unknown custom code
                for symbol, data in market_data.items():
                    signals.append({
                        "signal_type": "hold",
                        "symbol": symbol,
                        "signal_strength": Decimal("0.50"),
                        "price": Decimal(str(data["prices"][-1])),
                        "confidence_score": Decimal("0.30"),  # Low confidence for unknown code
                        "signal_data": {"custom_strategy": True},
                        "created_at": datetime.now(timezone.utc)
                    })
        
        except Exception as e:
            # Log error and return empty signals for safety
            print(f"Error executing custom strategy code: {e}")
            return []
        
        return signals