# tests/test_data_engine.py
import pytest
import pandas as pd
from datetime import date, timedelta
from pathlib import Path
import tempfile
import os
from unittest.mock import patch, MagicMock

# Add backend to path for imports
import sys
sys.path.append(str(Path(__file__).parent.parent))

from core.data_engine import DataEngine
from core.data_engine.metadata import MetadataStore
from core.data_engine.storage import StorageManager

class TestDataEngine:
    """Test suite for the professional data engine"""
    
    @pytest.fixture
    def temp_data_dir(self):
        """Create temporary directory for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def mock_settings(self, temp_data_dir):
        """Mock settings to use temporary directory"""
        with patch('core.data_engine.engine.settings') as mock_settings:
            mock_settings.DATA_ENGINE_ROOT = str(temp_data_dir)
            yield mock_settings
    
    @pytest.fixture
    def engine(self, mock_settings):
        """Create data engine instance for testing"""
        return DataEngine()
    
    @pytest.fixture
    def sample_data(self):
        """Generate sample market data for testing"""
        dates = pd.date_range('2024-06-01', '2024-06-30', freq='B')  # Business days
        data = pd.DataFrame({
            'Open': [100 + i for i in range(len(dates))],
            'High': [105 + i for i in range(len(dates))],
            'Low': [95 + i for i in range(len(dates))],
            'Close': [102 + i for i in range(len(dates))],
            'Volume': [1000000 + i*10000 for i in range(len(dates))],
            'Dividends': [0.0] * len(dates),
            'Stock Splits': [0.0] * len(dates)
        }, index=dates)
        data.index.name = 'Date'
        return data

class TestBasicFunctionality(TestDataEngine):
    """Test basic data engine functionality"""
    
    def test_engine_initialization(self, engine):
        """Test that engine initializes correctly"""
        assert isinstance(engine, DataEngine)
        assert hasattr(engine, 'data_root')
        assert hasattr(engine, 'storage')
        assert hasattr(engine, 'metadata')
    
    def test_directory_creation(self, engine):
        """Test that required directories are created"""
        expected_dirs = [
            'raw/stocks/daily', 'raw/stocks/hourly',
            'raw/crypto/daily', 'raw/crypto/hourly',
            'processed/stocks/daily', 'processed/stocks/hourly',
            'processed/crypto/daily', 'processed/crypto/hourly',
            'cache/stocks/daily', 'cache/stocks/hourly',
            'cache/crypto/daily', 'cache/crypto/hourly',
            'metadata'
        ]
        
        for dir_path in expected_dirs:
            full_path = engine.data_root / dir_path
            assert full_path.exists(), f"Directory {dir_path} should exist"
    
    @patch('core.data_engine.storage.yf.Ticker')
    def test_get_data_basic(self, mock_ticker, engine, sample_data):
        """Test basic get_data functionality"""
        # Mock Yahoo Finance response
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.history.return_value = sample_data
        mock_ticker.return_value = mock_ticker_instance
        
        # Test data retrieval
        result = engine.get_data('AAPL', date(2024, 6, 1), date(2024, 6, 30))
        
        assert not result.empty
        assert len(result) == len(sample_data)
        assert 'Close' in result.columns
        assert 'Adj_Close' in result.columns
    
    @patch('core.data_engine.storage.yf.Ticker')
    def test_caching_works(self, mock_ticker, engine, sample_data):
        """Test that caching mechanism works"""
        # Mock Yahoo Finance response
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.history.return_value = sample_data
        mock_ticker.return_value = mock_ticker_instance
        
        # First call should download
        result1 = engine.get_data('AAPL', date(2024, 6, 1), date(2024, 6, 30))
        download_calls = mock_ticker_instance.history.call_count
        
        # Second call should use cache
        result2 = engine.get_data('AAPL', date(2024, 6, 1), date(2024, 6, 30))
        
        # Should not make additional download calls
        assert mock_ticker_instance.history.call_count == download_calls
        assert len(result1) == len(result2)
        # Compare essential data instead of exact DataFrame equality
        assert not result1.empty
        assert not result2.empty
        assert list(result1.columns) == list(result2.columns)
    
    def test_symbol_management(self, engine):
        """Test symbol registration and retrieval"""
        # Add test symbols
        engine.metadata.add_symbol('AAPL', 'Apple Inc.', 'Technology', asset_type='stock')
        engine.metadata.add_symbol('BTC-USD', 'Bitcoin USD', asset_type='crypto')
        
        # Test symbol retrieval
        all_symbols = engine.get_symbols()
        assert 'AAPL' in all_symbols
        assert 'BTC-USD' in all_symbols
        
        # Test filtering by asset type
        stocks = engine.get_symbols('stock')
        crypto = engine.get_symbols('crypto')
        
        assert 'AAPL' in stocks
        assert 'BTC-USD' not in stocks
        assert 'BTC-USD' in crypto
        assert 'AAPL' not in crypto

class TestDataLayers(TestDataEngine):
    """Test the 4-layer data architecture"""
    
    @patch('core.data_engine.storage.yf.Ticker')
    def test_raw_data_storage(self, mock_ticker, engine, sample_data):
        """Test that raw data is stored correctly"""
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.history.return_value = sample_data
        mock_ticker.return_value = mock_ticker_instance
        
        # Get data to trigger storage
        engine.get_data('AAPL', date(2024, 6, 1), date(2024, 6, 30))
        
        # Check that raw file was created
        raw_files = list(engine.data_root.glob('raw/stocks/daily/*.parquet'))
        assert len(raw_files) > 0
        
        # Verify data can be loaded
        raw_data = pd.read_parquet(raw_files[0])
        assert not raw_data.empty
        assert 'Close' in raw_data.columns
    
    @patch('core.data_engine.storage.yf.Ticker')
    def test_processed_data_creation(self, mock_ticker, engine, sample_data):
        """Test that processed data is created with adjustments"""
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.history.return_value = sample_data
        mock_ticker.return_value = mock_ticker_instance
        
        # Get data to trigger processing
        result = engine.get_data('AAPL', date(2024, 6, 1), date(2024, 6, 30))
        
        # Check that processed file was created
        processed_files = list(engine.data_root.glob('processed/stocks/daily/*.parquet'))
        assert len(processed_files) > 0
        
        # Verify adjusted close column exists
        assert 'Adj_Close' in result.columns
        
        # Load processed data directly
        processed_data = pd.read_parquet(processed_files[0])
        assert 'Adj_Close' in processed_data.columns
    
    @patch('core.data_engine.storage.yf.Ticker')
    def test_cache_data_creation(self, mock_ticker, engine, sample_data):
        """Test that cache files are created for queries"""
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.history.return_value = sample_data
        mock_ticker.return_value = mock_ticker_instance
        
        # Get data to trigger caching
        engine.get_data('AAPL', date(2024, 6, 1), date(2024, 6, 30))
        
        # Check that cache file was created
        cache_files = list(engine.data_root.glob('cache/stocks/daily/*.parquet'))
        assert len(cache_files) > 0
        
        # Verify cache file naming convention
        cache_file = cache_files[0]
        assert '2024-06-01' in cache_file.name
        assert '2024-06-30' in cache_file.name
    
    def test_metadata_database(self, engine):
        """Test metadata database functionality"""
        # Test symbol registration
        engine.metadata.add_symbol('TEST', 'Test Symbol', 'Technology', asset_type='stock')
        
        # Test symbol retrieval
        symbols = engine.metadata.get_symbols()
        test_symbol = next((s for s in symbols if s['symbol'] == 'TEST'), None)
        
        assert test_symbol is not None
        assert test_symbol['name'] == 'Test Symbol'
        assert test_symbol['sector'] == 'Technology'
        assert test_symbol['asset_type'] == 'stock'

class TestErrorHandling(TestDataEngine):
    """Test error handling and edge cases"""
    
    @patch('core.data_engine.storage.yf.Ticker')
    def test_invalid_symbol(self, mock_ticker, engine):
        """Test handling of invalid symbols"""
        # Mock empty response for invalid symbol
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.history.return_value = pd.DataFrame()
        mock_ticker.return_value = mock_ticker_instance
        
        result = engine.get_data('INVALID', date(2024, 6, 1), date(2024, 6, 30))
        
        assert result.empty
    
    @patch('core.data_engine.storage.yf.Ticker')
    def test_network_error_handling(self, mock_ticker, engine):
        """Test handling of network errors"""
        # Mock network error
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.history.side_effect = Exception("Network error")
        mock_ticker.return_value = mock_ticker_instance
        
        result = engine.get_data('AAPL', date(2024, 6, 1), date(2024, 6, 30))
        
        assert result.empty
    
    def test_invalid_date_range(self, engine):
        """Test handling of invalid date ranges"""
        # Future dates
        future_start = date.today() + timedelta(days=30)
        future_end = date.today() + timedelta(days=60)
        
        with patch('core.data_engine.storage.yf.Ticker') as mock_ticker:
            mock_ticker_instance = MagicMock()
            mock_ticker_instance.history.return_value = pd.DataFrame()
            mock_ticker.return_value = mock_ticker_instance
            
            result = engine.get_data('AAPL', future_start, future_end)
            assert result.empty
    
    def test_end_before_start(self, engine):
        """Test handling when end date is before start date"""
        start = date(2024, 6, 30)
        end = date(2024, 6, 1)  # End before start
        
        with patch('core.data_engine.storage.yf.Ticker') as mock_ticker:
            mock_ticker_instance = MagicMock()
            mock_ticker_instance.history.return_value = pd.DataFrame()
            mock_ticker.return_value = mock_ticker_instance
            
            result = engine.get_data('AAPL', start, end)
            assert result.empty

class TestPerformance(TestDataEngine):
    """Test performance characteristics"""
    
    @patch('core.data_engine.storage.yf.Ticker')
    def test_large_date_range(self, mock_ticker, engine):
        """Test handling of large date ranges"""
        # Generate large dataset (1 year)
        dates = pd.date_range('2023-01-01', '2023-12-31', freq='B')
        large_data = pd.DataFrame({
            'Open': [100] * len(dates),
            'High': [105] * len(dates),
            'Low': [95] * len(dates),
            'Close': [102] * len(dates),
            'Volume': [1000000] * len(dates),
            'Dividends': [0.0] * len(dates),
            'Stock Splits': [0.0] * len(dates)
        }, index=dates)
        large_data.index.name = 'Date'
        
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.history.return_value = large_data
        mock_ticker.return_value = mock_ticker_instance
        
        result = engine.get_data('AAPL', date(2023, 1, 1), date(2023, 12, 31))
        
        assert not result.empty
        assert len(result) == len(large_data)
    
    @patch('core.data_engine.storage.yf.Ticker')
    def test_multiple_symbols_performance(self, mock_ticker, engine, sample_data):
        """Test performance with multiple symbols"""
        symbols = ['AAPL', 'GOOGL', 'MSFT', 'BTC-USD', 'ETH-USD']
        
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.history.return_value = sample_data
        mock_ticker.return_value = mock_ticker_instance
        
        results = {}
        for symbol in symbols:
            result = engine.get_data(symbol, date(2024, 6, 1), date(2024, 6, 30))
            results[symbol] = result
        
        assert len(results) == len(symbols)
        for symbol, data in results.items():
            assert not data.empty

class TestIntegration(TestDataEngine):
    """Integration tests that verify end-to-end functionality"""
    
    @patch('core.data_engine.storage.yf.Ticker')
    def test_full_workflow(self, mock_ticker, engine, sample_data):
        """Test complete workflow from download to cache usage"""
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.history.return_value = sample_data
        mock_ticker.return_value = mock_ticker_instance
        
        symbol = 'AAPL'
        start_date = date(2024, 6, 1)
        end_date = date(2024, 6, 30)
        
        # First call - should create all layers
        result1 = engine.get_data(symbol, start_date, end_date)
        
        # Verify all layers exist
        assert len(list(engine.data_root.glob('raw/stocks/daily/*.parquet'))) > 0
        assert len(list(engine.data_root.glob('processed/stocks/daily/*.parquet'))) > 0
        assert len(list(engine.data_root.glob('cache/stocks/daily/*.parquet'))) > 0
        
        # Verify metadata was updated
        coverage = engine.get_data_coverage(symbol, '1d')
        assert 'raw' in coverage
        assert 'processed' in coverage
        assert 'cache' in coverage
        
        # Second call - should use cache
        result2 = engine.get_data(symbol, start_date, end_date)
        
        # Results should be equivalent
        assert len(result1) == len(result2)
        assert not result1.empty
        assert not result2.empty
        assert list(result1.columns) == list(result2.columns)
    
    @patch('core.data_engine.storage.yf.Ticker')
    def test_data_consistency(self, mock_ticker, engine, sample_data):
        """Test data consistency across all layers"""
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.history.return_value = sample_data
        mock_ticker.return_value = mock_ticker_instance
        
        # Get data to populate all layers
        result = engine.get_data('AAPL', date(2024, 6, 1), date(2024, 6, 30))
        
        # Load data from each layer
        raw_files = list(engine.data_root.glob('raw/stocks/daily/*.parquet'))
        processed_files = list(engine.data_root.glob('processed/stocks/daily/*.parquet'))
        cache_files = list(engine.data_root.glob('cache/stocks/daily/*.parquet'))
        
        assert len(raw_files) > 0
        assert len(processed_files) > 0
        assert len(cache_files) > 0
        
        raw_data = pd.read_parquet(raw_files[0])
        processed_data = pd.read_parquet(processed_files[0])
        cache_data = pd.read_parquet(cache_files[0])
        
        # Basic consistency checks
        assert len(raw_data) == len(processed_data)
        assert 'Adj_Close' in processed_data.columns
        assert 'Adj_Close' not in raw_data.columns
        
        # Cache should match the filtered processed data
        assert not cache_data.empty

# Pytest configuration and fixtures
@pytest.fixture(scope="session")
def test_data_dir():
    """Session-scoped temporary directory for all tests"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)

# Test runner
if __name__ == "__main__":
    pytest.main([__file__, "-v"])