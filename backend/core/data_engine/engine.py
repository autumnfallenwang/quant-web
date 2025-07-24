# core/data_engine/engine.py
import pandas as pd
from datetime import date, timedelta
from pathlib import Path
from typing import Optional
from core.settings import settings
from .metadata import MetadataStore
from .storage import StorageManager

class DataEngine:
    """
    Professional 4-layer data engine:
    1. Raw - Original downloads (immutable)
    2. Processed - Adjusted data (split/dividend adjusted)
    3. Cache - Query results (fast access)
    4. Metadata - File tracking (SQLite)
    """
    
    def __init__(self):
        self.data_root = Path(settings.DATA_ENGINE_ROOT)
        self.storage = StorageManager(self.data_root)
        self.metadata = MetadataStore(self.data_root / 'metadata' / 'symbols.db')
    
    def get_data(self, symbol: str, start: date, end: date, interval: str = '1d') -> pd.DataFrame:
        """
        Get market data - tries cache first, then processed, then downloads raw
        
        Args:
            symbol: Stock/crypto symbol
            start: Start date
            end: End date  
            interval: Data interval ('1d', '1h')
            
        Returns:
            DataFrame with market data
        """
        # Register symbol if new
        self.metadata.add_symbol(symbol)
        
        # Try cache first
        cached_data = self._get_cached_data(symbol, start, end, interval)
        if cached_data is not None and not cached_data.empty:
            return cached_data
        
        # Try processed data
        processed_data = self._get_processed_data(symbol, start, end, interval)
        if processed_data is not None and not processed_data.empty:
            # Cache the result
            self._cache_data(symbol, processed_data, start, end, interval)
            return processed_data
        
        # Download raw data
        raw_data = self._ensure_raw_data(symbol, start, end, interval)
        if raw_data.empty:
            return raw_data
        
        # Process raw data
        processed_data = self.storage.process_raw_data(raw_data)
        if not processed_data.empty:
            self._save_processed_data(symbol, processed_data, start, end, interval)
            
            # Filter to requested range
            filtered_data = self._filter_data(processed_data, start, end)
            
            # Cache the result
            self._cache_data(symbol, filtered_data, start, end, interval)
            return filtered_data
        
        return pd.DataFrame()
    
    def _get_cached_data(self, symbol: str, start: date, end: date, interval: str) -> Optional[pd.DataFrame]:
        """Check cache for exact query"""
        cache_files = self.metadata.get_data_files(symbol, interval, 'cache', start, end)
        
        for file_info in cache_files:
            file_path = Path(file_info['file_path'])
            if file_path.exists():
                data = self.storage.load_data(file_path)
                if data is not None:
                    return self._filter_data(data, start, end)
        
        return None
    
    def _get_processed_data(self, symbol: str, start: date, end: date, interval: str) -> Optional[pd.DataFrame]:
        """Load from processed data files"""
        processed_files = self.metadata.get_data_files(symbol, interval, 'processed', start, end)
        
        all_data = []
        for file_info in processed_files:
            file_path = Path(file_info['file_path'])
            if file_path.exists():
                data = self.storage.load_data(file_path)
                if data is not None:
                    all_data.append(data)
        
        if all_data:
            combined = pd.concat(all_data).sort_index()
            return self._filter_data(combined, start, end)
        
        return None
    
    def _ensure_raw_data(self, symbol: str, start: date, end: date, interval: str) -> pd.DataFrame:
        """Ensure raw data exists, download if necessary"""
        # Check if we have raw data covering the range
        raw_files = self.metadata.get_data_files(symbol, interval, 'raw', start, end)
        
        all_data = []
        for file_info in raw_files:
            file_path = Path(file_info['file_path'])
            if file_path.exists():
                data = self.storage.load_data(file_path)
                if data is not None:
                    all_data.append(data)
        
        if all_data:
            combined = pd.concat(all_data).sort_index()
            filtered = self._filter_data(combined, start, end)
            
            # Check if we have sufficient coverage
            if not filtered.empty and self._is_coverage_sufficient(filtered, start, end):
                return filtered
        
        # Download missing data
        print(f"Downloading {symbol} data from {start} to {end}")
        raw_data = self.storage.download_raw_data(symbol, start, end, interval)
        
        if not raw_data.empty:
            # Save raw data
            self._save_raw_data(symbol, raw_data, interval)
            
        return raw_data
    
    def _save_raw_data(self, symbol: str, data: pd.DataFrame, interval: str):
        """Save raw data and register in metadata"""
        if data.empty:
            return
            
        start_date = data.index.min().date()
        end_date = data.index.max().date()
        
        file_path = self.storage.get_file_path(symbol, interval, 'raw', start_date, end_date)
        self.storage.save_data(data, file_path)
        
        # Register in metadata
        file_info = self.storage.get_file_info(file_path)
        self.metadata.register_data_file(
            symbol, interval, 'raw', start_date, end_date,
            str(file_path), file_info.get('row_count'), file_info.get('file_size')
        )
    
    def _save_processed_data(self, symbol: str, data: pd.DataFrame, start: date, end: date, interval: str):
        """Save processed data and register in metadata"""
        if data.empty:
            return
            
        data_start = data.index.min().date()
        data_end = data.index.max().date()
        
        file_path = self.storage.get_file_path(symbol, interval, 'processed', data_start, data_end)
        self.storage.save_data(data, file_path)
        
        # Register in metadata
        file_info = self.storage.get_file_info(file_path)
        self.metadata.register_data_file(
            symbol, interval, 'processed', data_start, data_end,
            str(file_path), file_info.get('row_count'), file_info.get('file_size')
        )
    
    def _cache_data(self, symbol: str, data: pd.DataFrame, start: date, end: date, interval: str):
        """Cache query result"""
        if data.empty:
            return
            
        file_path = self.storage.get_file_path(symbol, interval, 'cache', start, end)
        self.storage.save_data(data, file_path)
        
        # Register in metadata
        file_info = self.storage.get_file_info(file_path)
        self.metadata.register_data_file(
            symbol, interval, 'cache', start, end,
            str(file_path), file_info.get('row_count'), file_info.get('file_size')
        )
    
    def _filter_data(self, data: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
        """Filter data to requested date range"""
        if data.empty:
            return data
            
        # Convert to timezone-naive timestamps for comparison
        start_ts = pd.Timestamp(start).tz_localize(None)
        end_ts = pd.Timestamp(end).tz_localize(None)
        
        # Ensure data index is timezone-naive
        if data.index.tz is not None:
            data_index = data.index.tz_convert('UTC').tz_localize(None)
        else:
            data_index = data.index
            
        mask = (data_index >= start_ts) & (data_index <= end_ts)
        return data[mask].copy()
    
    def _is_coverage_sufficient(self, data: pd.DataFrame, start: date, end: date) -> bool:
        """Check if data adequately covers the requested range"""
        if data.empty:
            return False
            
        # Convert to timezone-aware dates for comparison
        data_start = data.index.min()
        data_end = data.index.max()
        
        if data_start.tz is not None:
            data_start = data_start.tz_convert('UTC').date()
            data_end = data_end.tz_convert('UTC').date()
        else:
            data_start = data_start.date()
            data_end = data_end.date()
        
        # Allow some flexibility for weekends/holidays
        start_buffer = start - timedelta(days=5)
        end_buffer = end + timedelta(days=5)
        
        return data_start <= start_buffer and data_end >= end_buffer
    
    def get_symbols(self, asset_type: str = None) -> list:
        """Get available symbols"""
        symbols = self.metadata.get_symbols(asset_type)
        return [s['symbol'] for s in symbols]
    
    def get_data_coverage(self, symbol: str, interval: str = '1d') -> dict:
        """Get data coverage information for symbol"""
        return self.metadata.get_data_coverage(symbol, interval)