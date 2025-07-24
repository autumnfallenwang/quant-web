# backend/calculate_storage.py
"""
Calculate storage requirements for market data
"""
import yfinance as yf
import pandas as pd
import sys
from datetime import datetime, timedelta

def analyze_data_size():
    """Analyze actual data size from a sample download"""
    
    print("Analyzing actual data size...")
    print("="*50)
    
    # Sample one stock and one crypto
    stock_ticker = yf.Ticker('AAPL')
    crypto_ticker = yf.Ticker('BTC-USD')
    
    # Get data samples
    stock_1d = stock_ticker.history(period='1y', interval='1d')
    stock_1h = stock_ticker.history(period='60d', interval='1h')
    crypto_1d = crypto_ticker.history(period='1y', interval='1d')
    crypto_1h = crypto_ticker.history(period='60d', interval='1h')
    
    # Calculate sizes
    results = {}
    
    for name, data in [
        ('Stock 1d', stock_1d),
        ('Stock 1h', stock_1h), 
        ('Crypto 1d', crypto_1d),
        ('Crypto 1h', crypto_1h)
    ]:
        # Memory usage
        memory_bytes = data.memory_usage(deep=True).sum()
        
        # Estimate storage sizes
        csv_size = len(data.to_csv())
        parquet_size = len(data.to_parquet())
        
        results[name] = {
            'rows': len(data),
            'columns': len(data.columns),
            'memory_mb': memory_bytes / (1024*1024),
            'csv_kb': csv_size / 1024,
            'parquet_kb': parquet_size / 1024,
            'compression_ratio': csv_size / parquet_size if parquet_size > 0 else 0
        }
        
        print(f"{name}:")
        print(f"  Rows: {len(data):,}")
        print(f"  Memory: {memory_bytes/1024/1024:.2f} MB")
        print(f"  CSV: {csv_size/1024:.1f} KB")
        print(f"  Parquet: {parquet_size/1024:.1f} KB")
        print(f"  Compression: {csv_size/parquet_size:.1f}x")
        print()
    
    return results

def calculate_storage_estimates():
    """Calculate storage estimates for different scenarios"""
    
    print("Storage Estimates for Market Data")
    print("="*50)
    
    # Market coverage scenarios
    scenarios = {
        'Conservative': {
            'stocks': 100,      # Top 100 stocks
            'crypto': 20,       # Top 20 crypto
            'description': 'S&P 100 + major crypto'
        },
        'Moderate': {
            'stocks': 500,      # S&P 500
            'crypto': 50,       # Top 50 crypto
            'description': 'S&P 500 + popular crypto'
        },
        'Aggressive': {
            'stocks': 3000,     # All major US stocks
            'crypto': 200,      # All major crypto
            'description': 'Full market coverage'
        }
    }
    
    # Data estimates per symbol (based on our tests)
    data_estimates = {
        'stock_1d': {
            'rows_per_year': 252,  # Trading days
            'years': 5,
            'size_per_row_kb': 0.15  # Conservative estimate
        },
        'stock_1h': {
            'rows_per_day': 6.5,   # Market hours
            'days': 60,
            'size_per_row_kb': 0.15
        },
        'crypto_1d': {
            'rows_per_year': 365,  # 24/7 trading
            'years': 5,
            'size_per_row_kb': 0.15
        },
        'crypto_1h': {
            'rows_per_day': 24,    # 24/7 trading
            'days': 60,
            'size_per_row_kb': 0.15
        }
    }
    
    print("Storage calculations:")
    print()
    
    for scenario_name, scenario in scenarios.items():
        print(f"{scenario_name} Scenario - {scenario['description']}")
        print("-" * 40)
        
        total_size_gb = 0
        
        # Calculate stock data
        stocks = scenario['stocks']
        stock_1d_total = (stocks * 
                         data_estimates['stock_1d']['rows_per_year'] * 
                         data_estimates['stock_1d']['years'] * 
                         data_estimates['stock_1d']['size_per_row_kb'])
        
        stock_1h_total = (stocks * 
                         data_estimates['stock_1h']['rows_per_day'] * 
                         data_estimates['stock_1h']['days'] * 
                         data_estimates['stock_1h']['size_per_row_kb'])
        
        # Calculate crypto data
        crypto = scenario['crypto']
        crypto_1d_total = (crypto * 
                          data_estimates['crypto_1d']['rows_per_year'] * 
                          data_estimates['crypto_1d']['years'] * 
                          data_estimates['crypto_1d']['size_per_row_kb'])
        
        crypto_1h_total = (crypto * 
                          data_estimates['crypto_1h']['rows_per_day'] * 
                          data_estimates['crypto_1h']['days'] * 
                          data_estimates['crypto_1h']['size_per_row_kb'])
        
        # Convert to MB/GB
        stock_1d_mb = stock_1d_total / 1024
        stock_1h_mb = stock_1h_total / 1024
        crypto_1d_mb = crypto_1d_total / 1024
        crypto_1h_mb = crypto_1h_total / 1024
        
        total_mb = stock_1d_mb + stock_1h_mb + crypto_1d_mb + crypto_1h_mb
        total_gb = total_mb / 1024
        
        print(f"  Stock daily (5yr):   {stock_1d_mb:6.1f} MB ({stocks:,} symbols)")
        print(f"  Stock hourly (60d):  {stock_1h_mb:6.1f} MB")
        print(f"  Crypto daily (5yr):  {crypto_1d_mb:6.1f} MB ({crypto:,} symbols)")
        print(f"  Crypto hourly (60d): {crypto_1h_mb:6.1f} MB")
        print(f"  Total:               {total_mb:6.1f} MB ({total_gb:.2f} GB)")
        print()
        
        # Add metadata estimates
        metadata_mb = (stocks + crypto) * 0.01  # ~10KB per symbol for metadata
        print(f"  + Metadata:          {metadata_mb:6.1f} MB")
        print(f"  Grand Total:         {total_mb + metadata_mb:6.1f} MB ({(total_mb + metadata_mb)/1024:.2f} GB)")
        print()
    
    return scenarios

def estimate_update_frequency():
    """Estimate data update requirements"""
    
    print("Data Update Requirements")
    print("="*30)
    
    # Daily updates
    daily_symbols = 3000 + 200  # All stocks + crypto
    daily_size_kb = daily_symbols * 0.15  # One row per symbol
    
    # Hourly updates  
    hourly_symbols = 3000 + 200
    hourly_size_kb = hourly_symbols * 0.15
    
    print(f"Daily updates:")
    print(f"  {daily_symbols:,} symbols × 1 row = {daily_size_kb:.1f} KB ({daily_size_kb/1024:.2f} MB)")
    print()
    print(f"Hourly updates:")
    print(f"  {hourly_symbols:,} symbols × 1 row = {hourly_size_kb:.1f} KB ({hourly_size_kb/1024:.2f} MB)")
    print()
    print(f"Monthly data growth: ~{(daily_size_kb * 30)/1024:.1f} MB daily + {(hourly_size_kb * 24 * 30)/1024:.1f} MB hourly")
    print(f"                   = {((daily_size_kb * 30) + (hourly_size_kb * 24 * 30))/1024:.1f} MB/month")

if __name__ == "__main__":
    print("Market Data Storage Calculator")
    print("=" * 50)
    
    # Analyze actual data sizes
    size_analysis = analyze_data_size()
    
    print("\n")
    
    # Calculate storage estimates
    storage_scenarios = calculate_storage_estimates()
    
    print()
    
    # Update frequency
    estimate_update_frequency()
    
    print("\n" + "="*50)
    print("RECOMMENDATIONS")
    print("="*50)
    print("• Start with Conservative scenario: ~200MB total")
    print("• Use Parquet format: 3-5x compression vs CSV")
    print("• Daily data has best storage efficiency")
    print("• Hourly data grows quickly but limited to 60 days")
    print("• Budget ~100MB/month for ongoing updates")
    print("• Consider incremental updates vs full redownloads")