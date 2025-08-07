# tests/data_engine/test_data_service_internal_api.py
"""
Tests for DataService internal API methods used by other engines
"""
import pytest
import pandas as pd
from datetime import date, timedelta
from unittest.mock import Mock, patch, AsyncMock
from services.data_service import DataService


@pytest.fixture
def data_service():
    """Create DataService instance for testing"""
    return DataService()


@pytest.fixture
def mock_data_engine():
    """Mock DataEngine for testing"""
    mock_engine = Mock()
    return mock_engine


@pytest.fixture
def sample_dataframe():
    """Sample DataFrame for testing"""
    dates = pd.date_range('2024-01-01', periods=5, freq='D')
    return pd.DataFrame({
        'Open': [100.0, 101.0, 102.0, 103.0, 104.0],
        'High': [105.0, 106.0, 107.0, 108.0, 109.0],
        'Low': [95.0, 96.0, 97.0, 98.0, 99.0],
        'Close': [102.0, 103.0, 104.0, 105.0, 106.0],
        'Volume': [1000, 1100, 1200, 1300, 1400]
    }, index=dates)


class TestDataServiceInternalAPI:
    """Test DataService internal API methods"""

    @pytest.mark.asyncio
    async def test_get_market_data_success(self, data_service, mock_data_engine, sample_dataframe):
        """Test successful market data retrieval for multiple symbols"""
        # Setup
        symbols = ['AAPL', 'MSFT']
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 5)
        
        # Mock the data engine to return sample data
        mock_data_engine.get_data.return_value = sample_dataframe
        data_service.data_engine = mock_data_engine
        
        # Execute
        result = await data_service.get_market_data(symbols, start_date, end_date)
        
        # Assert
        assert len(result) == 2
        assert 'AAPL' in result
        assert 'MSFT' in result
        assert isinstance(result['AAPL'], pd.DataFrame)
        assert len(result['AAPL']) == 5
        assert result['AAPL']['Close'].iloc[-1] == 106.0

    @pytest.mark.asyncio
    async def test_get_market_data_empty_data(self, data_service, mock_data_engine):
        """Test market data retrieval when no data is available"""
        # Setup
        symbols = ['INVALID']
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 5)
        
        # Mock empty DataFrame
        mock_data_engine.get_data.return_value = pd.DataFrame()
        data_service.data_engine = mock_data_engine
        
        # Execute
        result = await data_service.get_market_data(symbols, start_date, end_date)
        
        # Assert
        assert len(result) == 1
        assert result['INVALID'] is None

    @pytest.mark.asyncio
    async def test_get_market_data_with_error(self, data_service, mock_data_engine):
        """Test market data retrieval when engine throws error"""
        # Setup
        symbols = ['ERROR_SYMBOL']
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 5)
        
        # Mock error
        mock_data_engine.get_data.side_effect = Exception("Data fetch error")
        data_service.data_engine = mock_data_engine
        
        # Execute
        result = await data_service.get_market_data(symbols, start_date, end_date)
        
        # Assert
        assert len(result) == 1
        assert result['ERROR_SYMBOL'] is None

    @pytest.mark.asyncio
    async def test_get_current_prices_success(self, data_service, mock_data_engine, sample_dataframe):
        """Test successful current price retrieval"""
        # Setup
        symbols = ['AAPL', 'MSFT', 'GOOGL']
        
        # Mock the data engine
        mock_data_engine.get_data.return_value = sample_dataframe
        data_service.data_engine = mock_data_engine
        
        # Execute
        result = await data_service.get_current_prices(symbols)
        
        # Assert
        assert len(result) == 3
        assert result['AAPL'] == 106.0  # Last close price from sample data
        assert result['MSFT'] == 106.0
        assert result['GOOGL'] == 106.0

    @pytest.mark.asyncio
    async def test_get_current_prices_no_data(self, data_service, mock_data_engine):
        """Test current price retrieval when no data available"""
        # Setup
        symbols = ['INVALID']
        
        # Mock empty DataFrame
        mock_data_engine.get_data.return_value = pd.DataFrame()
        data_service.data_engine = mock_data_engine
        
        # Execute
        result = await data_service.get_current_prices(symbols)
        
        # Assert
        assert len(result) == 1
        assert result['INVALID'] is None

    @pytest.mark.asyncio
    async def test_get_symbol_data_success(self, data_service, mock_data_engine, sample_dataframe):
        """Test single symbol data retrieval"""
        # Setup
        symbol = 'AAPL'
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 5)
        
        mock_data_engine.get_data.return_value = sample_dataframe
        data_service.data_engine = mock_data_engine
        
        # Execute
        result = await data_service.get_symbol_data(symbol, start_date, end_date)
        
        # Assert
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 5
        assert result['Close'].iloc[-1] == 106.0

    @pytest.mark.asyncio
    async def test_get_symbol_data_no_data(self, data_service, mock_data_engine):
        """Test single symbol data retrieval with no data"""
        # Setup
        symbol = 'INVALID'
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 5)
        
        mock_data_engine.get_data.return_value = pd.DataFrame()
        data_service.data_engine = mock_data_engine
        
        # Execute
        result = await data_service.get_symbol_data(symbol, start_date, end_date)
        
        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_ensure_data_available_all_available(self, data_service, mock_data_engine, sample_dataframe):
        """Test ensure_data_available when all symbols have data"""
        # Setup
        symbols = ['AAPL', 'MSFT']
        
        mock_data_engine.get_data.return_value = sample_dataframe
        data_service.data_engine = mock_data_engine
        
        # Execute
        result = await data_service.ensure_data_available(symbols)
        
        # Assert
        assert len(result) == 2
        assert result['AAPL'] is True
        assert result['MSFT'] is True

    @pytest.mark.asyncio
    async def test_ensure_data_available_needs_refresh(self, data_service, mock_data_engine):
        """Test ensure_data_available when symbols need refresh"""
        # Setup
        symbols = ['AAPL', 'MSFT']
        
        # Mock no data initially, then successful refresh
        mock_data_engine.get_data.side_effect = [
            pd.DataFrame(),  # AAPL - no data initially
            pd.DataFrame(),  # MSFT - no data initially
        ]
        
        data_service.data_engine = mock_data_engine
        
        # Mock the refresh method to return success
        with patch.object(data_service, '_refresh_specific_symbols') as mock_refresh:
            mock_refresh.return_value = [
                {'symbol': 'AAPL', 'success': True},
                {'symbol': 'MSFT', 'success': True}
            ]
            
            # Execute
            result = await data_service.ensure_data_available(symbols)
            
            # Assert
            assert len(result) == 2
            assert result['AAPL'] is True  # Should be True after refresh
            assert result['MSFT'] is True
            mock_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_data_available_partial_failure(self, data_service, mock_data_engine, sample_dataframe):
        """Test ensure_data_available with mixed results"""
        # Setup
        symbols = ['AAPL', 'INVALID']
        
        # Mock: AAPL has data, INVALID doesn't
        def mock_get_data(symbol, start, end, interval):
            if symbol == 'AAPL':
                return sample_dataframe
            else:
                return pd.DataFrame()
        
        mock_data_engine.get_data.side_effect = mock_get_data
        data_service.data_engine = mock_data_engine
        
        # Mock refresh to fail for INVALID
        with patch.object(data_service, '_refresh_specific_symbols') as mock_refresh:
            mock_refresh.return_value = [
                {'symbol': 'INVALID', 'success': False, 'error': 'Symbol not found'}
            ]
            
            # Execute
            result = await data_service.ensure_data_available(symbols)
            
            # Assert
            assert len(result) == 2
            assert result['AAPL'] is True   # Had data initially
            assert result['INVALID'] is False  # Refresh failed

    def test_get_symbol_dataframe_success(self, data_service, mock_data_engine, sample_dataframe):
        """Test _get_symbol_dataframe internal method"""
        # Setup
        symbol = 'AAPL'
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 5)
        
        mock_data_engine.get_data.return_value = sample_dataframe
        data_service.data_engine = mock_data_engine
        
        # Execute
        result = data_service._get_symbol_dataframe(symbol, start_date, end_date, '1d')
        
        # Assert
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 5

    def test_get_symbol_dataframe_empty(self, data_service, mock_data_engine):
        """Test _get_symbol_dataframe with empty data"""
        # Setup
        symbol = 'INVALID'
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 5)
        
        mock_data_engine.get_data.return_value = pd.DataFrame()
        data_service.data_engine = mock_data_engine
        
        # Execute
        result = data_service._get_symbol_dataframe(symbol, start_date, end_date, '1d')
        
        # Assert
        assert result is None

    def test_get_current_price_success(self, data_service, mock_data_engine, sample_dataframe):
        """Test _get_current_price internal method"""
        # Setup
        symbol = 'AAPL'
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 5)
        
        mock_data_engine.get_data.return_value = sample_dataframe
        data_service.data_engine = mock_data_engine
        
        # Execute
        result = data_service._get_current_price(symbol, start_date, end_date)
        
        # Assert
        assert result == 106.0  # Last close price

    def test_get_current_price_no_data(self, data_service, mock_data_engine):
        """Test _get_current_price with no data"""
        # Setup
        symbol = 'INVALID'
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 5)
        
        mock_data_engine.get_data.return_value = pd.DataFrame()
        data_service.data_engine = mock_data_engine
        
        # Execute
        result = data_service._get_current_price(symbol, start_date, end_date)
        
        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_refresh_specific_symbols(self, data_service):
        """Test _refresh_specific_symbols method"""
        # Setup
        symbols = ['AAPL', 'MSFT']
        
        # Mock the _refresh_single_symbol method
        with patch.object(data_service, '_refresh_single_symbol') as mock_refresh:
            mock_refresh.side_effect = [
                {'symbol': 'AAPL', 'success': True, 'rows': 30},
                {'symbol': 'MSFT', 'success': True, 'rows': 30}
            ]
            
            # Execute
            result = await data_service._refresh_specific_symbols(symbols, 30)
            
            # Assert
            assert len(result) == 2
            assert result[0]['symbol'] == 'AAPL'
            assert result[0]['success'] is True
            assert result[1]['symbol'] == 'MSFT'
            assert result[1]['success'] is True


class TestDataServiceIntegration:
    """Integration tests for DataService internal API"""

    def test_internal_api_methods_exist(self):
        """Test that all required internal API methods exist"""
        service = DataService()
        
        # Check all internal API methods exist
        assert hasattr(service, 'get_market_data')
        assert hasattr(service, 'get_current_prices')
        assert hasattr(service, 'get_symbol_data')
        assert hasattr(service, 'ensure_data_available')
        
        # Check they are async methods
        import asyncio
        assert asyncio.iscoroutinefunction(service.get_market_data)
        assert asyncio.iscoroutinefunction(service.get_current_prices)
        assert asyncio.iscoroutinefunction(service.get_symbol_data)
        assert asyncio.iscoroutinefunction(service.ensure_data_available)

    def test_method_signatures(self):
        """Test that internal API methods have correct signatures"""
        service = DataService()
        
        # Check method signatures using inspection
        import inspect
        
        # get_market_data signature
        sig = inspect.signature(service.get_market_data)
        params = list(sig.parameters.keys())
        assert 'symbols' in params
        assert 'start_date' in params
        assert 'end_date' in params
        assert 'interval' in params
        
        # get_current_prices signature
        sig = inspect.signature(service.get_current_prices)
        params = list(sig.parameters.keys())
        assert 'symbols' in params
        
        # get_symbol_data signature
        sig = inspect.signature(service.get_symbol_data)
        params = list(sig.parameters.keys())
        assert 'symbol' in params
        assert 'start_date' in params
        assert 'end_date' in params
        assert 'interval' in params

    @pytest.mark.asyncio
    async def test_data_service_backwards_compatibility(self, data_service):
        """Test that existing DataService functionality still works"""
        # Test that original methods still exist and work
        tracked_symbols = data_service.get_tracked_symbols()
        
        assert 'stocks' in tracked_symbols
        assert 'crypto' in tracked_symbols
        assert 'total' in tracked_symbols
        assert len(tracked_symbols['stocks']) > 0
        assert len(tracked_symbols['crypto']) > 0
        
        # Test symbol management still works
        original_count = len(data_service.sp500_symbols)
        data_service.add_symbol('TEST', 'stock')
        assert len(data_service.sp500_symbols) == original_count + 1
        
        data_service.remove_symbol('TEST')
        assert len(data_service.sp500_symbols) == original_count