# tests/backtesting_engine/test_backtesting_api_real_http.py
"""
Real HTTP level tests for Backtesting API
Tests against running uvicorn server at http://localhost:8000
"""
import requests
import json
import time
from datetime import datetime


class TestBacktestingAPIReal:
    """Real HTTP tests for Backtesting API"""
    
    BASE_URL = "http://localhost:8000"
    
    def __init__(self):
        self.auth_token = None
        self.user_id = None
        self.workspace_id = 1
        self.strategy_id = None
        self.backtest_id = None
    
    def test_01_auth_login(self):
        """Test authentication to get token"""
        print("🧪 Test 1: Authentication")
        
        # Login with existing user credentials
        login_data = {
            "username": "john_user",
            "password": "SuperSecret123!"
        }
        
        try:
            response = requests.post(
                f"{self.BASE_URL}/auth/login", 
                json=login_data,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"Login status: {response.status_code}")
            
            if response.status_code == 200:
                token_data = response.json()
                self.auth_token = token_data["access_token"]
                print("✅ Authentication successful")
                print(f"   Token type: {token_data.get('token_type', 'Bearer')}")
                return True
            else:
                print(f"❌ Login failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Auth error: {e}")
            return False
    
    @property
    def headers(self):
        """Get auth headers"""
        return {"Authorization": f"Bearer {self.auth_token}"} if self.auth_token else {}
    
    def test_02_create_strategy_for_backtest(self):
        """Create a strategy to use for backtesting"""
        print("\\n🧪 Test 2: Create Strategy for Backtesting")
        
        import time
        unique_name = f"Backtest Strategy {int(time.time())}"
        
        strategy_data = {
            "name": unique_name,
            "strategy_type": "momentum",
            "description": "Strategy for backtesting tests",
            "risk_level": "medium",
            "is_public": False,
            "parameters": [
                {
                    "name": "period",
                    "type": "int",
                    "default_value": "20",
                    "current_value": "20",
                    "description": "Moving average period"
                }
            ]
        }
        
        try:
            response = requests.post(
                f"{self.BASE_URL}/workspace/{self.workspace_id}/strategies",
                json=strategy_data,
                headers=self.headers
            )
            
            print(f"Create strategy status: {response.status_code}")
            
            if response.status_code == 201:
                strategy = response.json()
                self.strategy_id = strategy["id"]
                print(f"✅ Strategy created: ID={self.strategy_id}, Name='{strategy['name']}'")
                return True
            else:
                print(f"❌ Strategy creation failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Create strategy error: {e}")
            return False
    
    def test_03_create_backtest(self):
        """Test backtest creation"""
        print("\\n🧪 Test 3: Create Backtest")
        
        if not self.strategy_id:
            print("❌ No strategy ID available")
            return False
        
        import time
        unique_name = f"Test Backtest {int(time.time())}"
        
        backtest_data = {
            "name": unique_name,
            "strategy_id": self.strategy_id,
            "start_date": "2024-01-01T00:00:00Z",
            "end_date": "2024-01-31T23:59:59Z",
            "initial_capital": 100000.0,
            "symbols": ["AAPL", "MSFT", "GOOGL"],
            "description": "Test backtest via HTTP API",
            "commission_per_share": 0.01,
            "slippage": 0.001
        }
        
        try:
            response = requests.post(
                f"{self.BASE_URL}/workspace/{self.workspace_id}/backtests",
                json=backtest_data,
                headers=self.headers
            )
            
            print(f"Create backtest status: {response.status_code}")
            
            if response.status_code == 201:
                backtest = response.json()
                self.backtest_id = backtest["id"]
                print(f"✅ Backtest created: ID={self.backtest_id}, Name='{backtest['name']}'")
                print(f"   Strategy: {backtest['strategy_id']}, Capital: ${backtest['initial_capital']}")
                print(f"   Symbols: {backtest['symbols']}")
                print(f"   Status: {backtest['status']}")
                return True
            else:
                print(f"❌ Backtest creation failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Create backtest error: {e}")
            return False
    
    def test_04_get_backtest_details(self):
        """Test getting backtest details"""
        print("\\n🧪 Test 4: Get Backtest Details")
        
        if not self.backtest_id:
            print("❌ No backtest ID available")
            return False
        
        try:
            response = requests.get(
                f"{self.BASE_URL}/workspace/{self.workspace_id}/backtests/{self.backtest_id}",
                headers=self.headers
            )
            
            print(f"Get backtest status: {response.status_code}")
            
            if response.status_code == 200:
                backtest = response.json()
                print(f"✅ Backtest retrieved: {backtest['name']}")
                print(f"   ID: {backtest['backtest_id']}")
                print(f"   Status: {backtest['status']}")
                print(f"   Date range: {backtest['start_date']} to {backtest['end_date']}")
                print(f"   Initial capital: ${backtest['initial_capital']}")
                return True
            else:
                print(f"❌ Get backtest failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Get backtest error: {e}")
            return False
    
    def test_05_list_backtests(self):
        """Test listing backtests in workspace"""
        print("\\n🧪 Test 5: List Backtests")
        
        try:
            response = requests.get(
                f"{self.BASE_URL}/workspace/{self.workspace_id}/backtests",
                params={"limit": 10},
                headers=self.headers
            )
            
            print(f"List backtests status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Backtests retrieved: {result.get('total_count', 0)} total")
                print(f"   Current page: {result.get('page', 1)}")
                print(f"   Page size: {result.get('page_size', 0)}")
                
                backtests = result.get('backtests', [])
                if backtests:
                    print(f"   Showing first {min(3, len(backtests))} backtests:")
                    for i, bt in enumerate(backtests[:3]):
                        print(f"     {i+1}. {bt.get('name', 'Unknown')} (Status: {bt.get('status', 'unknown')})")
                
                return True
            else:
                print(f"❌ List backtests failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ List backtests error: {e}")
            return False
    
    def test_06_start_backtest(self):
        """Test starting backtest execution"""
        print("\\n🧪 Test 6: Start Backtest Execution")
        
        if not self.backtest_id:
            print("❌ No backtest ID available")
            return False
        
        try:
            response = requests.post(
                f"{self.BASE_URL}/workspace/{self.workspace_id}/backtests/{self.backtest_id}/start",
                headers=self.headers
            )
            
            print(f"Start backtest status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                job_id = result.get("job_id")
                print(f"✅ Backtest execution started")
                print(f"   Job ID: {job_id}")
                print(f"   Status: {result.get('status')}")
                print(f"   Message: {result.get('message')}")
                print(f"   Estimated duration: {result.get('estimated_duration')} seconds")
                return True
            else:
                print(f"❌ Start backtest failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Start backtest error: {e}")
            return False
    
    def test_07_get_backtest_results_before_completion(self):
        """Test getting backtest results while still running"""
        print("\\n🧪 Test 7: Get Backtest Results (Before Completion)")
        
        if not self.backtest_id:
            print("❌ No backtest ID available")
            return False
        
        try:
            response = requests.get(
                f"{self.BASE_URL}/workspace/{self.workspace_id}/backtests/{self.backtest_id}/results",
                headers=self.headers
            )
            
            print(f"Get results status: {response.status_code}")
            
            # Should return 202 (Accepted) if still running
            if response.status_code == 202:
                result = response.json()
                print(f"✅ Backtest still processing")
                print(f"   Status: {result.get('status')}")
                print(f"   Message: {result.get('message')}")
                return True
            elif response.status_code == 200:
                result = response.json()
                print(f"✅ Backtest completed faster than expected")
                print(f"   Total return: ${result.get('total_return', 0)}")
                print(f"   Return percentage: {result.get('return_percentage', 0):.2%}")
                return True
            else:
                print(f"❌ Get results failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Get results error: {e}")
            return False
    
    def test_08_cancel_backtest(self):
        """Test cancelling backtest"""
        print("\\n🧪 Test 8: Cancel Backtest")
        
        if not self.backtest_id:
            print("❌ No backtest ID available")
            return False
        
        try:
            response = requests.post(
                f"{self.BASE_URL}/workspace/{self.workspace_id}/backtests/{self.backtest_id}/cancel",
                headers=self.headers
            )
            
            print(f"Cancel backtest status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Backtest cancelled")
                print(f"   Message: {result.get('message')}")
                print(f"   Backtest ID: {result.get('backtest_id')}")
                return True
            elif response.status_code == 400:
                # Already completed or not cancellable
                result = response.json()
                print(f"✅ Backtest not cancellable (expected): {result.get('detail')}")
                return True  # This is expected behavior
            else:
                print(f"❌ Cancel backtest failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Cancel backtest error: {e}")
            return False
    
    def test_09_get_workspace_summary(self):
        """Test getting workspace backtest summary"""
        print("\\n🧪 Test 9: Get Workspace Backtest Summary")
        
        try:
            response = requests.get(
                f"{self.BASE_URL}/workspace/{self.workspace_id}/backtest-analytics",
                headers=self.headers
            )
            
            print(f"Get summary status: {response.status_code}")
            
            if response.status_code == 200:
                summary = response.json()
                print(f"✅ Workspace summary retrieved")
                print(f"   Total backtests: {summary.get('total_backtests', 0)}")
                print(f"   Completed: {summary.get('completed_backtests', 0)}")
                print(f"   Running: {summary.get('running_backtests', 0)}")
                print(f"   Failed: {summary.get('failed_backtests', 0)}")
                
                if summary.get('avg_return_percentage'):
                    print(f"   Avg return: {float(summary.get('avg_return_percentage', 0)):.2%}")
                
                return True
            else:
                print(f"❌ Get summary failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Get summary error: {e}")
            return False
    
    def test_10_validation_errors(self):
        """Test API validation errors"""
        print("\\n🧪 Test 10: API Validation Errors")
        
        # Test invalid backtest creation
        invalid_data = {
            "name": "",  # Empty name
            "strategy_id": 99999,  # Non-existent strategy
            "start_date": "invalid-date",
            "end_date": "2024-01-01T00:00:00Z",  # End before start
            "initial_capital": -1000  # Negative capital
        }
        
        try:
            response = requests.post(
                f"{self.BASE_URL}/workspace/{self.workspace_id}/backtests",
                json=invalid_data,
                headers=self.headers
            )
            
            print(f"Invalid backtest status: {response.status_code}")
            
            if response.status_code == 400 or response.status_code == 422:
                print("✅ Validation errors correctly caught")
                result = response.json()
                print(f"   Error: {result.get('detail', 'Unknown error')}")
                return True
            else:
                print(f"❌ Expected validation error, got: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Validation test error: {e}")
            return False
    
    def run_all_tests(self):
        """Run all tests in sequence"""
        print("="*60)
        print("🚀 BACKTESTING API REAL HTTP TESTS")
        print("Testing complete Backtesting Engine via HTTP API")
        print("="*60)
        
        tests = [
            self.test_01_auth_login,
            self.test_02_create_strategy_for_backtest,
            self.test_03_create_backtest,
            self.test_04_get_backtest_details,
            self.test_05_list_backtests,
            self.test_06_start_backtest,
            self.test_07_get_backtest_results_before_completion,
            self.test_08_cancel_backtest,
            self.test_09_get_workspace_summary,
            self.test_10_validation_errors
        ]
        
        passed = 0
        failed = 0
        
        for test in tests:
            try:
                if test():
                    passed += 1
                else:
                    failed += 1
                time.sleep(1)  # Brief pause between tests
            except Exception as e:
                print(f"❌ Test failed with exception: {e}")
                failed += 1
        
        print("\\n" + "="*60)
        print("📊 TEST RESULTS")
        print("="*60)
        print(f"✅ PASSED: {passed}")
        print(f"❌ FAILED: {failed}")
        print(f"📈 SUCCESS RATE: {passed/(passed+failed)*100:.1f}%")
        
        if failed == 0:
            print("\\n🎉 ALL TESTS PASSED! Backtesting Engine HTTP API working!")
        else:
            print(f"\\n⚠️  {failed} tests failed. Check implementation.")
        
        print("="*60)


if __name__ == "__main__":
    tester = TestBacktestingAPIReal()
    tester.run_all_tests()