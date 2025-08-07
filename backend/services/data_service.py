# services/data_service.py - Data engine service layer
"""
Service layer for market data operations and symbol management.
Handles data refresh, symbol tracking, and coverage analysis.
"""
# Standard library imports
from datetime import date, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging

# Third-party imports
import pandas as pd

# Local imports
from core.data_engine import DataEngine

logger = logging.getLogger(__name__)

class DataService:
    """
    Service for market data operations and symbol management.
    Provides data refresh capabilities and symbol tracking.
    """
    
    def __init__(self):
        self.data_engine = DataEngine()
        
        # Predefined symbol lists
        self.sp500_symbols = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK-B', 
            'UNH', 'JNJ', 'JPM', 'V', 'PG', 'HD', 'CVX', 'MA', 'PFE', 'ABBV',
            'BAC', 'KO', 'AVGO', 'PEP', 'TMO', 'COST', 'WMT', 'DIS', 'ABT',
            'MRK', 'ACN', 'VZ', 'NFLX', 'ADBE', 'DHR', 'TXN', 'NKE', 'QCOM',
            'LIN', 'WFC', 'BMY', 'UPS', 'T', 'PM', 'SPGI', 'RTX', 'LOW', 'HON',
            'MS', 'IBM', 'NEE', 'INTU', 'CAT', 'GS'  # Top 50 for now
        ]
        
        self.top_cryptos = [
            'BTC-USD', 'ETH-USD', 'BNB-USD', 'XRP-USD', 'ADA-USD', 
            'DOGE-USD', 'MATIC-USD', 'SOL-USD', 'DOT-USD', 'LTC-USD',
            'SHIB-USD', 'TRX-USD', 'AVAX-USD', 'UNI-USD', 'ATOM-USD',
            'LINK-USD', 'XMR-USD', 'ETC-USD', 'BCH-USD', 'ALGO-USD'  # Top 20
        ]
    
    async def refresh_all_symbols(self, days_back: int = 30, interval: str = '1d') -> Dict:
        """
        Refresh data for all tracked symbols
        
        Args:
            days_back: How many days of recent data to refresh
            interval: Data interval ('1d', '1h')
            
        Returns:
            Dict with refresh results
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)
        
        all_symbols = self.sp500_symbols + self.top_cryptos
        
        logger.info(f"Starting data refresh for {len(all_symbols)} symbols")
        logger.info(f"Date range: {start_date} to {end_date}, interval: {interval}")
        
        results = {
            'success': [],
            'failed': [],
            'skipped': [],
            'summary': {
                'total_symbols': len(all_symbols),
                'start_date': str(start_date),
                'end_date': str(end_date),
                'interval': interval
            }
        }
        
        # Use ThreadPoolExecutor for parallel downloads
        with ThreadPoolExecutor(max_workers=5) as executor:
            # Create tasks for all symbols
            tasks = []
            for symbol in all_symbols:
                task = asyncio.get_event_loop().run_in_executor(
                    executor, 
                    self._refresh_single_symbol, 
                    symbol, start_date, end_date, interval
                )
                tasks.append((symbol, task))
            
            # Wait for all tasks to complete
            for symbol, task in tasks:
                try:
                    result = await task
                    if result['success']:
                        results['success'].append(result)
                        logger.info(f"✅ {symbol}: {result['rows']} rows")
                    else:
                        results['failed'].append(result)
                        logger.warning(f"❌ {symbol}: {result['error']}")
                        
                except Exception as e:
                    error_result = {
                        'symbol': symbol,
                        'success': False,
                        'error': str(e),
                        'rows': 0
                    }
                    results['failed'].append(error_result)
                    logger.error(f"💥 {symbol}: {e}")
        
        # Update summary
        results['summary']['successful'] = len(results['success'])
        results['summary']['failed'] = len(results['failed'])
        results['summary']['success_rate'] = len(results['success']) / len(all_symbols) * 100
        
        logger.info(f"Refresh complete: {results['summary']['successful']}/{len(all_symbols)} successful")
        
        return results
    
    def _refresh_single_symbol(self, symbol: str, start: date, end: date, interval: str) -> Dict:
        """Refresh data for a single symbol"""
        try:
            data = self.data_engine.get_data(symbol, start, end, interval)
            
            if not data.empty:
                return {
                    'symbol': symbol,
                    'success': True,
                    'rows': len(data),
                    'date_range': f"{data.index.min().date()} to {data.index.max().date()}",
                    'latest_price': float(data['Close'].iloc[-1])
                }
            else:
                return {
                    'symbol': symbol,
                    'success': False,
                    'error': 'No data returned',
                    'rows': 0
                }
                
        except Exception as e:
            return {
                'symbol': symbol,
                'success': False,
                'error': str(e),
                'rows': 0
            }
    
    async def refresh_sp500_only(self, days_back: int = 30) -> Dict:
        """Refresh only S&P 500 stocks"""
        logger.info("Refreshing S&P 500 data only")
        # Temporarily override symbols list
        original_cryptos = self.top_cryptos
        self.top_cryptos = []  # Skip cryptos
        
        result = await self.refresh_all_symbols(days_back)
        
        # Restore original list
        self.top_cryptos = original_cryptos
        return result
    
    async def refresh_crypto_only(self, days_back: int = 30) -> Dict:
        """Refresh only crypto data"""
        logger.info("Refreshing crypto data only")
        # Temporarily override symbols list
        original_stocks = self.sp500_symbols
        self.sp500_symbols = []  # Skip stocks
        
        result = await self.refresh_all_symbols(days_back)
        
        # Restore original list
        self.sp500_symbols = original_stocks
        return result
    
    def get_tracked_symbols(self) -> Dict[str, List[str]]:
        """Get list of all tracked symbols"""
        return {
            'stocks': self.sp500_symbols.copy(),
            'crypto': self.top_cryptos.copy(),
            'total': len(self.sp500_symbols) + len(self.top_cryptos)
        }
    
    def add_symbol(self, symbol: str, asset_type: str = 'auto'):
        """Add a symbol to tracking list"""
        if asset_type == 'auto':
            asset_type = 'crypto' if '-USD' in symbol else 'stock'
            
        if asset_type == 'stock' and symbol not in self.sp500_symbols:
            self.sp500_symbols.append(symbol)
            logger.info(f"Added stock symbol: {symbol}")
        elif asset_type == 'crypto' and symbol not in self.top_cryptos:
            self.top_cryptos.append(symbol)
            logger.info(f"Added crypto symbol: {symbol}")
    
    def remove_symbol(self, symbol: str):
        """Remove a symbol from tracking"""
        if symbol in self.sp500_symbols:
            self.sp500_symbols.remove(symbol)
            logger.info(f"Removed stock symbol: {symbol}")
        elif symbol in self.top_cryptos:
            self.top_cryptos.remove(symbol)
            logger.info(f"Removed crypto symbol: {symbol}")
    
    async def get_data_coverage_summary(self) -> Dict:
        """Get summary of data coverage for all symbols"""
        all_symbols = self.sp500_symbols + self.top_cryptos
        
        coverage_summary = {
            'stocks': {},
            'crypto': {},
            'total_symbols': len(all_symbols),
            'coverage_stats': {
                'full_coverage': 0,
                'partial_coverage': 0,
                'no_coverage': 0
            }
        }
        
        for symbol in all_symbols:
            try:
                coverage = self.data_engine.get_data_coverage(symbol, '1d')
                asset_type = 'crypto' if '-USD' in symbol else 'stocks'
                coverage_summary[asset_type][symbol] = coverage
                
                # Categorize coverage
                if coverage and 'raw' in coverage and 'processed' in coverage:
                    coverage_summary['coverage_stats']['full_coverage'] += 1
                elif coverage:
                    coverage_summary['coverage_stats']['partial_coverage'] += 1
                else:
                    coverage_summary['coverage_stats']['no_coverage'] += 1
                    
            except Exception as e:
                logger.warning(f"Error getting coverage for {symbol}: {e}")
                coverage_summary['coverage_stats']['no_coverage'] += 1
        
        return coverage_summary
    
    # ===============================
    # Internal API Methods (for other engines)
    # ===============================
    
    async def get_market_data(
        self, 
        symbols: List[str], 
        start_date: date, 
        end_date: date, 
        interval: str = '1d'
    ) -> Dict[str, Optional[pd.DataFrame]]:
        """Get market data for multiple symbols (for Strategy/Backtesting engines)"""
        logger.info(f"Getting market data for {len(symbols)} symbols from {start_date} to {end_date}")
        
        market_data = {}
        
        # Use ThreadPoolExecutor for parallel data fetching
        with ThreadPoolExecutor(max_workers=5) as executor:
            tasks = []
            for symbol in symbols:
                task = asyncio.get_event_loop().run_in_executor(
                    executor,
                    self._get_symbol_dataframe,
                    symbol, start_date, end_date, interval
                )
                tasks.append((symbol, task))
            
            # Wait for all tasks to complete
            for symbol, task in tasks:
                try:
                    df = await task
                    market_data[symbol] = df  # Can be None if no data
                except Exception as e:
                    logger.error(f"Error getting data for {symbol}: {e}")
                    market_data[symbol] = None
        
        successful_count = len([v for v in market_data.values() if v is not None and not v.empty])
        logger.info(f"Retrieved data for {successful_count}/{len(symbols)} symbols")
        
        return market_data
    
    async def get_current_prices(self, symbols: List[str]) -> Dict[str, Optional[float]]:
        """Get current prices for symbols (for Portfolio engine)"""
        logger.info(f"Getting current prices for {len(symbols)} symbols")
        
        # Get data for last 2 days to ensure we have current price
        end_date = date.today()
        start_date = end_date - timedelta(days=2)
        
        prices = {}
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            tasks = []
            for symbol in symbols:
                task = asyncio.get_event_loop().run_in_executor(
                    executor,
                    self._get_current_price,
                    symbol, start_date, end_date
                )
                tasks.append((symbol, task))
            
            for symbol, task in tasks:
                try:
                    price = await task
                    prices[symbol] = price  # Can be None if no data
                except Exception as e:
                    logger.error(f"Error getting current price for {symbol}: {e}")
                    prices[symbol] = None
        
        successful_prices = len([p for p in prices.values() if p is not None])
        logger.info(f"Retrieved current prices for {successful_prices}/{len(symbols)} symbols")
        
        return prices
    
    async def get_symbol_data(
        self, 
        symbol: str, 
        start_date: date, 
        end_date: date, 
        interval: str = '1d'
    ) -> Optional[pd.DataFrame]:
        """Get data for a single symbol (convenience method)"""
        result = await self.get_market_data([symbol], start_date, end_date, interval)
        return result.get(symbol)
    
    async def ensure_data_available(self, symbols: List[str], days_back: int = 7) -> Dict[str, bool]:
        """Ensure symbols have recent data, refresh if needed (for engine initialization)"""
        logger.info(f"Ensuring data availability for {len(symbols)} symbols")
        
        availability = {}
        symbols_to_refresh = []
        
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)
        
        # Check which symbols need refreshing
        for symbol in symbols:
            try:
                df = self.data_engine.get_data(symbol, start_date, end_date, '1d')
                if not df.empty and len(df) >= min(days_back, 3):  # At least 3 data points or days requested
                    availability[symbol] = True
                else:
                    symbols_to_refresh.append(symbol)
                    availability[symbol] = False
            except Exception as e:
                logger.warning(f"Error checking availability for {symbol}: {e}")
                symbols_to_refresh.append(symbol)
                availability[symbol] = False
        
        # Refresh symbols that need updating
        if symbols_to_refresh:
            logger.info(f"Refreshing data for {len(symbols_to_refresh)} symbols")
            
            # Add symbols to tracking if not already tracked
            for symbol in symbols_to_refresh:
                self.add_symbol(symbol)
            
            # Refresh the symbols
            refresh_result = await self._refresh_specific_symbols(symbols_to_refresh, days_back)
            
            # Update availability based on refresh results
            for symbol in symbols_to_refresh:
                success = any(r.get('symbol') == symbol and r.get('success', False) for r in refresh_result)
                availability[symbol] = success
        
        successful_count = len([v for v in availability.values() if v])
        logger.info(f"Data available for {successful_count}/{len(symbols)} symbols")
        
        return availability
    
    def _get_symbol_dataframe(self, symbol: str, start: date, end: date, interval: str) -> Optional[pd.DataFrame]:
        """Get DataFrame for a single symbol (synchronous for executor)"""
        try:
            df = self.data_engine.get_data(symbol, start, end, interval)
            return df if not df.empty else None
        except Exception as e:
            logger.debug(f"Error getting data for {symbol}: {e}")
            return None
    
    def _get_current_price(self, symbol: str, start: date, end: date) -> Optional[float]:
        """Get current price for a single symbol (synchronous for executor)"""
        try:
            df = self.data_engine.get_data(symbol, start, end, '1d')
            if df.empty:
                return None
            return float(df['Close'].iloc[-1])
        except Exception as e:
            logger.debug(f"Error getting current price for {symbol}: {e}")
            return None
    
    async def _refresh_specific_symbols(self, symbols: List[str], days_back: int) -> List[Dict]:
        """Refresh specific symbols and return results"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)
        
        results = []
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            tasks = []
            for symbol in symbols:
                task = asyncio.get_event_loop().run_in_executor(
                    executor,
                    self._refresh_single_symbol,
                    symbol, start_date, end_date, '1d'
                )
                tasks.append((symbol, task))
            
            # Wait for all tasks to complete
            for symbol, task in tasks:
                try:
                    result = await task
                    results.append(result)
                except Exception as e:
                    results.append({
                        'symbol': symbol,
                        'success': False,
                        'error': str(e)
                    })
        
        return results

# Convenience functions for cron jobs
async def daily_refresh():
    """Daily data refresh - last 7 days"""
    service = DataService()
    return await service.refresh_all_symbols(days_back=7)

async def weekly_refresh(): 
    """Weekly data refresh - last 30 days"""
    service = DataService()
    return await service.refresh_all_symbols(days_back=30)

async def monthly_refresh():
    """Monthly data refresh - last 90 days"""
    service = DataService()
    return await service.refresh_all_symbols(days_back=90)