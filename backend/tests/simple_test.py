# tests/simple_test.py
"""
Simple manual test to verify data engine works
"""
import sys
from pathlib import Path
from datetime import date

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent))

from core.data_engine import DataEngine

def test_data_engine_manual():
    """Manual test of data engine"""
    print("🧪 Testing Data Engine")
    print("="*30)
    
    try:
        # Initialize engine
        engine = DataEngine()
        print("✅ Engine initialized")
        
        # Test with real data
        data = engine.get_data('AAPL', date(2024, 6, 1), date(2024, 6, 15))
        
        if not data.empty:
            print(f"✅ Got {len(data)} rows of data")
            print(f"📊 Columns: {list(data.columns)}")
            print(f"💰 Latest close: ${data['Close'].iloc[-1]:.2f}")
            
            # Test caching
            data2 = engine.get_data('AAPL', date(2024, 6, 1), date(2024, 6, 15))
            if len(data) == len(data2):
                print("✅ Caching works")
            else:
                print("⚠️ Caching issue")
        else:
            print("❌ No data returned")
        
        print("🎉 Test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_data_engine_manual()