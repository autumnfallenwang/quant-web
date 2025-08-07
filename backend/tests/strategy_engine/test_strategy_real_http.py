# tests/strategy_engine/test_strategy_real_http.py
"""
Real HTTP level tests for refactored Strategy API with DataService integration
Tests against running uvicorn server at http://localhost:8000
"""
import requests
import json
import time
from datetime import datetime


class TestStrategyAPIReal:
    """Real HTTP tests for Strategy API"""
    
    BASE_URL = "http://localhost:8000"
    
    def __init__(self):
        self.auth_token = None
        self.user_id = None
        self.workspace_id = 1
        self.strategy_id = None
    
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
    
    def test_02_create_strategy(self):
        """Test strategy creation"""
        print("\n🧪 Test 2: Create Strategy")
        
        import time
        unique_name = f"Test DataService Strategy {int(time.time())}"
        
        strategy_data = {
            "name": unique_name,
            "strategy_type": "momentum",
            "description": "Test strategy using DataService integration",
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
                print(f"   Type: {strategy['strategy_type']}, Parameters: {strategy.get('parameter_count', 0)}")
                return True
            else:
                print(f"❌ Strategy creation failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Create strategy error: {e}")
            return False
    
    def test_03_strategy_analysis_quick(self):
        """Test quick strategy analysis with DataService"""
        print("\n🧪 Test 3: Quick Strategy Analysis (with DataService)")
        
        if not self.strategy_id:
            print("❌ No strategy ID available")
            return False
        
        try:
            # Test with specific symbols in request body
            response = requests.post(
                f"{self.BASE_URL}/workspace/{self.workspace_id}/strategies/{self.strategy_id}/analyze",
                json={
                    "analysis_type": "quick",
                    "symbols": ["AAPL", "MSFT", "GOOGL"]
                },
                headers=self.headers
            )
            
            print(f"Analysis status: {response.status_code}")
            
            if response.status_code == 200:
                analysis = response.json()
                print(f"✅ Analysis completed for strategy {analysis['strategy_id']}")
                
                # Check performance metrics
                perf = analysis.get('performance_metrics', {})
                print(f"   Signals generated: {perf.get('signals_generated', 0)}")
                print(f"   Symbols analyzed: {perf.get('symbols_analyzed', 0)}")
                print(f"   Data availability: {perf.get('market_data_availability', 0):.1f}%")
                
                # Check signal analysis
                signals = analysis.get('signal_analysis', {})
                print(f"   Signal frequency: {signals.get('signal_frequency', 'unknown')}")
                print(f"   Total signals: {signals.get('total_signals', 0)}")
                
                # Check recommendations
                recommendations = analysis.get('recommendations', [])
                print(f"   Recommendations: {len(recommendations)}")
                for i, rec in enumerate(recommendations[:2]):
                    print(f"     {i+1}. {rec}")
                
                return True
            else:
                print(f"❌ Analysis failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Analysis error: {e}")
            return False
    
    def test_04_generate_signals_with_dataservice(self):
        """Test signal generation using DataService"""
        print("\n🧪 Test 4: Generate Signals (with DataService)")
        
        if not self.strategy_id:
            print("❌ No strategy ID available")
            return False
        
        try:
            response = requests.post(
                f"{self.BASE_URL}/workspace/{self.workspace_id}/strategies/{self.strategy_id}/signals/generate",
                json={
                    "symbols": ["AAPL", "MSFT"],
                    "lookback_days": 30
                },
                headers=self.headers
            )
            
            print(f"Signal generation status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Signals generated: {result['total_count']} signals")
                
                signals = result.get('signals', [])
                if signals:
                    print("   Sample signals:")
                    for i, signal in enumerate(signals[:3]):
                        print(f"     {i+1}. {signal['signal_type'].upper()} {signal['symbol']} - "
                              f"Strength: {signal['signal_strength']:.2f}, "
                              f"Confidence: {signal['confidence_score']:.2f}")
                else:
                    print("   No signals in response (signals stored in database)")
                
                return True
            else:
                print(f"❌ Signal generation failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Signal generation error: {e}")
            return False
    
    def test_05_backtest_deprecated_endpoint(self):
        """Test that backtest endpoint returns deprecation error"""
        print("\n🧪 Test 5: Backtest Endpoint (should be deprecated)")
        
        if not self.strategy_id:
            print("❌ No strategy ID available")
            return False
        
        try:
            backtest_data = {
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": "2024-01-31T00:00:00Z", 
                "initial_capital": 100000.0
            }
            
            response = requests.post(
                f"{self.BASE_URL}/workspace/{self.workspace_id}/strategies/{self.strategy_id}/backtest",
                json=backtest_data,
                headers=self.headers
            )
            
            print(f"Backtest status: {response.status_code}")
            
            if response.status_code == 501:
                error_data = response.json()
                print("✅ Backtest correctly deprecated")
                print(f"   Error: {error_data['detail']['error']}")
                print(f"   Migration: {error_data['detail']['migration_info']['new_endpoint']}")
                return True
            else:
                print(f"❌ Expected 501 deprecation error, got: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Backtest test error: {e}")
            return False
    
    def test_06_get_strategy_signals(self):
        """Test retrieving stored strategy signals"""
        print("\n🧪 Test 6: Get Strategy Signals")
        
        if not self.strategy_id:
            print("❌ No strategy ID available")
            return False
        
        try:
            response = requests.get(
                f"{self.BASE_URL}/workspace/{self.workspace_id}/strategies/{self.strategy_id}/signals",
                params={"limit": 10},
                headers=self.headers
            )
            
            print(f"Get signals status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Retrieved signals: {result.get('total_count', 0)} total")
                
                signals = result.get('signals', [])
                if signals:
                    print(f"   Showing {len(signals)} signals:")
                    for signal in signals[:3]:
                        print(f"     - {signal.get('signal_type', 'unknown')} signal for "
                              f"{signal.get('symbol', 'unknown')}")
                
                return True
            else:
                print(f"❌ Get signals failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Get signals error: {e}")
            return False
    
    def test_07_strategy_validation(self):
        """Test strategy validation"""
        print("\n🧪 Test 7: Strategy Validation")
        
        if not self.strategy_id:
            print("❌ No strategy ID available")
            return False
        
        try:
            response = requests.get(
                f"{self.BASE_URL}/workspace/{self.workspace_id}/strategies/{self.strategy_id}/validate",
                headers=self.headers
            )
            
            print(f"Validation status: {response.status_code}")
            
            if response.status_code == 200:
                validation = response.json()
                print(f"✅ Validation completed")
                print(f"   Valid: {validation.get('is_valid', False)}")
                print(f"   Issues: {len(validation.get('issues', []))}")
                print(f"   Warnings: {len(validation.get('warnings', []))}")
                
                return True
            else:
                print(f"❌ Validation failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Validation error: {e}")
            return False
    
    def test_08_comprehensive_analysis_job(self):
        """Test comprehensive analysis (background job) with specific symbols"""
        print("\n🧪 Test 8: Comprehensive Analysis (Background Job with Custom Symbols)")
        
        if not self.strategy_id:
            print("❌ No strategy ID available")
            return False
        
        try:
            # Test comprehensive analysis with specific symbols
            custom_symbols = ["AAPL", "TSLA", "NVDA"]
            response = requests.post(
                f"{self.BASE_URL}/workspace/{self.workspace_id}/strategies/{self.strategy_id}/analyze",
                json={
                    "analysis_type": "comprehensive",
                    "symbols": custom_symbols,
                    "include_risk_metrics": True,
                    "include_allocation": True
                },
                headers=self.headers
            )
            
            print(f"Comprehensive analysis status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                job_id = result.get('job_id')
                print(f"✅ Comprehensive analysis job started: {job_id}")
                print(f"   Analysis type: {result.get('analysis_type')}")
                print(f"   Custom symbols: {custom_symbols}")
                print(f"   Note: Symbols should now be passed to background job for processing")
                
                return True
            else:
                print(f"❌ Comprehensive analysis failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Comprehensive analysis error: {e}")
            return False
    
    def run_all_tests(self):
        """Run all tests in sequence"""
        print("="*60)
        print("🚀 STRATEGY API REAL HTTP TESTS")
        print("Testing refactored Strategy Engine with DataService integration")
        print("="*60)
        
        tests = [
            self.test_01_auth_login,
            self.test_02_create_strategy,
            self.test_03_strategy_analysis_quick,
            self.test_04_generate_signals_with_dataservice,
            self.test_05_backtest_deprecated_endpoint,
            self.test_06_get_strategy_signals,
            self.test_07_strategy_validation,
            self.test_08_comprehensive_analysis_job
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
        
        print("\n" + "="*60)
        print("📊 TEST RESULTS")
        print("="*60)
        print(f"✅ PASSED: {passed}")
        print(f"❌ FAILED: {failed}")
        print(f"📈 SUCCESS RATE: {passed/(passed+failed)*100:.1f}%")
        
        if failed == 0:
            print("\n🎉 ALL TESTS PASSED! Strategy Engine refactoring successful!")
        else:
            print(f"\n⚠️  {failed} tests failed. Check implementation.")
        
        print("="*60)


if __name__ == "__main__":
    tester = TestStrategyAPIReal()
    tester.run_all_tests()