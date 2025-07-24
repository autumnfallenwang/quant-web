# services/data_refresh_service.py
"""
Service for refreshing market data for all tracked symbols
"""
from datetime import date, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging

from core.data_engine import DataEngine

logger = logging.getLogger(__name__)

class DataRefreshService:
    """
    Service to refresh market data for predefined symbol lists
    Designed for cron jobs and scheduled updates
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

# Convenience functions for cron jobs
async def daily_refresh():
    """Daily data refresh - last 7 days"""
    service = DataRefreshService()
    return await service.refresh_all_symbols(days_back=7)

async def weekly_refresh(): 
    """Weekly data refresh - last 30 days"""
    service = DataRefreshService()
    return await service.refresh_all_symbols(days_back=30)

async def monthly_refresh():
    """Monthly data refresh - last 90 days"""
    service = DataRefreshService()
    return await service.refresh_all_symbols(days_back=90)