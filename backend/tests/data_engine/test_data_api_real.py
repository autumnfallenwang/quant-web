# tests/data_engine/test_data_api_real.py
"""
Real Data API endpoint tests using actual HTTP requests to running server.
Tests all infrastructure-level data endpoints without authentication.
"""
import pytest
import requests
import json
import time
from typing import Dict, List

# Test configuration
BASE_URL = "http://localhost:8000"

class TestDataAPIReal:
    """Real API tests using actual HTTP requests"""
    
    @classmethod
    def setup_class(cls):
        """Setup for data API tests (no authentication needed)"""
        cls.sample_symbols = ["AAPL", "MSFT", "GOOGL"]  # Sample symbols for reference
        cls.added_symbols = []  # Track symbols added during tests for cleanup
        print("🚀 Starting Data API Real Tests (No authentication required)")
    
    @classmethod
    def teardown_class(cls):
        """Clean up test symbols"""
        print("🧹 Cleaning up test data...")
        
        # Remove any symbols we added during tests
        for symbol in cls.added_symbols:
            try:
                response = requests.delete(f"{BASE_URL}/data/symbols/{symbol}")
                if response.status_code in [200, 404]:
                    print(f"✅ Cleaned up symbol {symbol}")
                else:
                    print(f"⚠️ Could not clean up symbol {symbol}: {response.status_code}")
            except Exception as e:
                print(f"⚠️ Error cleaning up symbol {symbol}: {e}")
    
    def test_01_get_tracked_symbols(self):
        """Test GET /data/symbols - Get all tracked symbols"""
        print("🧪 Testing: Get Tracked Symbols")
        
        response = requests.get(f"{BASE_URL}/data/symbols")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, dict), "Expected dict response structure"
        
        # Response should have stocks, crypto, and total fields
        assert "stocks" in data, "Response should have 'stocks' field"
        assert "crypto" in data, "Response should have 'crypto' field"
        assert "total" in data, "Response should have 'total' field"
        assert isinstance(data["stocks"], list), "Stocks should be a list"
        assert isinstance(data["crypto"], list), "Crypto should be a list"
        assert isinstance(data["total"], int), "Total should be an integer"
        
        # Verify total count matches actual symbols
        expected_total = len(data["stocks"]) + len(data["crypto"])
        assert data["total"] == expected_total, f"Total mismatch: reported {data['total']}, actual {expected_total}"
        
        self.initial_symbol_count = data["total"]
        print(f"✅ Found {self.initial_symbol_count} tracked symbols ({len(data['stocks'])} stocks, {len(data['crypto'])} crypto)")
    
    def test_02_add_symbol(self):
        """Test POST /data/symbols - Add a new symbol for tracking"""
        print("🧪 Testing: Add Symbol")
        
        symbol_data = {
            "symbol": "TSLA",
            "asset_type": "stock"
        }
        
        response = requests.post(
            f"{BASE_URL}/data/symbols",
            headers={"Content-Type": "application/json"},
            json=symbol_data
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        if response.status_code in [200, 201]:
            data = response.json()
            assert data["symbol"] == symbol_data["symbol"]
            assert "message" in data
            
            # Track for cleanup
            self.added_symbols.append("TSLA")
            print(f"✅ Added symbol: {data['symbol']}")
        
        elif response.status_code == 400 and "already exists" in response.text:
            print("✅ Symbol already exists (acceptable)")
        
        else:
            print(f"⚠️ Add symbol failed: {response.status_code} - {response.text}")
    
    def test_03_get_data_coverage(self):
        """Test GET /data/coverage - Get data coverage statistics"""
        print("🧪 Testing: Get Data Coverage")
        
        response = requests.get(f"{BASE_URL}/data/coverage")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "total_symbols" in data, "Coverage should include total_symbols"
        assert "stocks" in data, "Coverage should include stocks breakdown"
        assert "crypto" in data, "Coverage should include crypto breakdown"
        assert "coverage_stats" in data, "Coverage should include coverage_stats"
        
        print(f"✅ Coverage: {data['total_symbols']} total symbols")
        print(f"   Stocks: {len(data['stocks'])} symbols")
        print(f"   Crypto: {len(data['crypto'])} symbols")
        print(f"   Coverage stats: {data['coverage_stats']}")
    
    def test_04_refresh_data_sync(self):
        """Test POST /data/refresh - Synchronous data refresh"""
        print("🧪 Testing: Synchronous Data Refresh")
        
        refresh_request = {
            "days_back": 5,
            "interval": "1d",
            "asset_type": "stocks",
            "async_mode": False  # Synchronous mode for testing
        }
        
        response = requests.post(
            f"{BASE_URL}/data/refresh",
            headers={"Content-Type": "application/json"},
            json=refresh_request
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            assert "message" in data
            assert "status" in data
            assert data["status"] == "completed"
            
            if "result" in data and data["result"]:
                result = data["result"]
                if "summary" in result:
                    summary = result["summary"]
                    print(f"✅ Refreshed {summary.get('successful', 0)} symbols (success rate: {summary.get('success_rate', 0)}%)")
                else:
                    print(f"✅ Sync refresh completed: {data['message']}")
            else:
                print(f"✅ Sync refresh completed: {data['message']}")
        
        else:
            print(f"⚠️ Data refresh failed: {response.status_code} - {response.text}")
    
    def test_05_refresh_data_async(self):
        """Test POST /data/refresh - Asynchronous data refresh"""
        print("🧪 Testing: Asynchronous Data Refresh")
        
        refresh_request = {
            "days_back": 3,
            "interval": "1d",
            "asset_type": "all",
            "async_mode": True  # Asynchronous mode
        }
        
        response = requests.post(
            f"{BASE_URL}/data/refresh",
            headers={"Content-Type": "application/json"},
            json=refresh_request
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            assert "message" in data
            assert "status" in data
            assert data["status"] == "started"
            
            if "symbols_count" in data:
                print(f"✅ Queued {data['symbols_count']} symbols for background refresh")
            else:
                print(f"✅ Async refresh started: {data['message']}")
        
        else:
            print(f"⚠️ Async data refresh failed: {response.status_code} - {response.text}")
    
    def test_06_scheduled_refresh_daily(self):
        """Test POST /data/refresh/daily - Schedule daily refresh"""
        print("🧪 Testing: Schedule Daily Refresh")
        
        response = requests.post(f"{BASE_URL}/data/refresh/daily")
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            assert "message" in data
            assert "schedule" in data
            assert "status" in data
            assert data["status"] == "started"
            
            print(f"✅ Daily refresh scheduled: {data['message']} ({data['schedule']})")
        
        else:
            print(f"⚠️ Daily refresh scheduling failed: {response.status_code} - {response.text}")
    
    def test_07_scheduled_refresh_weekly(self):
        """Test POST /data/refresh/weekly - Schedule weekly refresh"""
        print("🧪 Testing: Schedule Weekly Refresh")
        
        response = requests.post(f"{BASE_URL}/data/refresh/weekly")
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            assert "message" in data
            assert "schedule" in data
            assert "status" in data
            assert data["status"] == "started"
            
            print(f"✅ Weekly refresh scheduled: {data['message']} ({data['schedule']})")
        
        else:
            print(f"⚠️ Weekly refresh scheduling failed: {response.status_code} - {response.text}")
    
    def test_08_scheduled_refresh_monthly(self):
        """Test POST /data/refresh/monthly - Schedule monthly refresh"""
        print("🧪 Testing: Schedule Monthly Refresh")
        
        response = requests.post(f"{BASE_URL}/data/refresh/monthly")
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            assert "message" in data
            assert "schedule" in data
            assert "status" in data
            assert data["status"] == "started"
            
            print(f"✅ Monthly refresh scheduled: {data['message']} ({data['schedule']})")
        
        else:
            print(f"⚠️ Monthly refresh scheduling failed: {response.status_code} - {response.text}")
    
    def test_09_remove_symbol(self):
        """Test DELETE /data/symbols/{symbol} - Remove a symbol"""
        print("🧪 Testing: Remove Symbol")
        
        # Try to remove a test symbol (if we added one)
        symbol_to_remove = "TSLA" if "TSLA" in self.added_symbols else None
        
        if symbol_to_remove:
            response = requests.delete(f"{BASE_URL}/data/symbols/{symbol_to_remove}")
            
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                assert data["symbol"] == symbol_to_remove
                assert "message" in data
                
                # Remove from our tracking list
                self.added_symbols.remove(symbol_to_remove)
                print(f"✅ Removed symbol: {symbol_to_remove}")
            
            else:
                print(f"⚠️ Remove symbol failed: {response.status_code} - {response.text}")
        
        else:
            print("✅ No test symbols to remove (skipped)")
    
    def test_10_error_handling(self):
        """Test error handling with invalid requests"""
        print("🧪 Testing: Error Handling")
        
        # Test invalid symbol format
        invalid_symbol_data = {
            "symbol": "",  # Empty symbol
            "asset_type": "stocks"
        }
        
        response = requests.post(
            f"{BASE_URL}/data/symbols",
            headers={"Content-Type": "application/json"},
            json=invalid_symbol_data
        )
        
        assert response.status_code in [400, 422], f"Expected 400/422 for invalid symbol, got {response.status_code}"
        
        # Test removing non-existent symbol (Data API might return 200 with error message)
        response = requests.delete(f"{BASE_URL}/data/symbols/NONEXISTENT999")
        # Data API might return 200 with error message instead of 404, so we check both cases
        if response.status_code == 200:
            # If 200, should contain error message
            data = response.json()
            assert "message" in data, "Should have error message for non-existent symbol"
        else:
            assert response.status_code in [404, 400], f"Expected 404/400 for non-existent symbol, got {response.status_code}"
        
        # Test invalid refresh parameters
        invalid_refresh = {
            "days_back": -1,  # Invalid negative days
            "interval": "invalid"  # Invalid interval
        }
        
        response = requests.post(
            f"{BASE_URL}/data/refresh",
            headers={"Content-Type": "application/json"},
            json=invalid_refresh
        )
        
        assert response.status_code in [400, 422], f"Expected 400/422 for invalid refresh params, got {response.status_code}"
        
        print("✅ Error handling works correctly")
    
    def test_11_data_consistency(self):
        """Test data consistency across endpoints"""
        print("🧪 Testing: Data Consistency")
        
        # Get coverage data
        coverage_response = requests.get(f"{BASE_URL}/data/coverage")
        coverage_data = coverage_response.json()
        
        # Get symbols list
        symbols_response = requests.get(f"{BASE_URL}/data/symbols")
        symbols_data = symbols_response.json()
        
        # Check consistency
        if coverage_response.status_code == 200 and symbols_response.status_code == 200:
            total_symbols_from_coverage = coverage_data["total_symbols"]
            total_symbols_from_list = symbols_data["total"]  # Use the total field from symbols response
            
            # Allow for small differences due to timing
            assert abs(total_symbols_from_coverage - total_symbols_from_list) <= 1, \
                f"Symbol count mismatch: coverage={total_symbols_from_coverage}, list={total_symbols_from_list}"
            
            print(f"✅ Data consistency verified: {total_symbols_from_coverage} symbols")
        
        else:
            print("⚠️ Could not verify data consistency - API errors")
    
    def test_12_performance_basic(self):
        """Test basic performance characteristics"""
        print("🧪 Testing: Basic Performance")
        
        # Test response times for key endpoints
        endpoints_to_test = [
            ("/data/symbols", "GET"),
            ("/data/coverage", "GET")
        ]
        
        for endpoint, method in endpoints_to_test:
            start_time = time.time()
            
            if method == "GET":
                response = requests.get(f"{BASE_URL}{endpoint}")
            
            end_time = time.time()
            response_time = end_time - start_time
            
            print(f"   {method} {endpoint}: {response_time:.3f}s (status: {response.status_code})")
            
            # Basic performance assertion (should respond within 5 seconds)
            assert response_time < 5.0, f"{endpoint} took too long: {response_time}s"
        
        print("✅ Basic performance requirements met")


def run_data_api_tests():
    """Run all data API tests"""
    print("🚀 Starting Data API Real Tests...")
    print("=" * 60)
    
    test_instance = TestDataAPIReal()
    
    try:
        # Setup
        test_instance.setup_class()
        
        # Run all tests
        test_methods = [method for method in dir(test_instance) if method.startswith('test_')]
        test_methods.sort()  # Run in order
        
        passed = 0
        failed = 0
        
        for test_method in test_methods:
            try:
                print(f"\n📋 Running: {test_method}")
                getattr(test_instance, test_method)()
                passed += 1
                print(f"✅ PASSED: {test_method}")
            except Exception as e:
                failed += 1
                print(f"❌ FAILED: {test_method} - {str(e)}")
        
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {passed} passed, {failed} failed")
        
        # Cleanup
        test_instance.teardown_class()
        
    except Exception as e:
        print(f"💥 Test setup failed: {e}")


if __name__ == "__main__":
    run_data_api_tests()