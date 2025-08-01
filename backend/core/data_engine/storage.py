# core/data_engine/storage.py
import pandas as pd
from pathlib import Path
from datetime import date
from typing import Optional
import yfinance as yf

class StorageManager:
    """
    Manages the 4-layer storage architecture:
    - raw: Original downloads
    - processed: Adjusted data  
    - cache: Query results
    - metadata: File tracking
    """
    
    def __init__(self, data_root: Path):
        self.data_root = data_root
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create directory structure"""
        for data_type in ['raw', 'processed', 'cache', 'metadata']:
            for asset_type in ['stocks', 'crypto']:
                for interval in ['daily', 'hourly']:
                    if data_type != 'metadata':
                        (self.data_root / data_type / asset_type / interval).mkdir(parents=True, exist_ok=True)
        
        # Metadata directory
        (self.data_root / 'metadata').mkdir(parents=True, exist_ok=True)
    
    def get_file_path(self, symbol: str, interval: str, data_type: str, 
                     start_date: date = None, end_date: date = None) -> Path:
        """Generate file path for data"""
        asset_type = 'crypto' if '-USD' in symbol else 'stocks'
        interval_dir = 'daily' if interval == '1d' else 'hourly'
        
        # Clean symbol for filename
        clean_symbol = symbol.replace('-', '_')
        
        if data_type == 'raw' or data_type == 'processed':
            # Year-based files for raw/processed
            year = start_date.year if start_date else date.today().year
            filename = f"{clean_symbol}_{year}.parquet"
        else:
            # Date-range based files for cache
            if start_date and end_date:
                filename = f"{clean_symbol}_{start_date}_{end_date}.parquet"
            else:
                filename = f"{clean_symbol}.parquet"
        
        return self.data_root / data_type / asset_type / interval_dir / filename
    
    def save_data(self, data: pd.DataFrame, file_path: Path):
        """Save DataFrame to parquet file, merging with existing data"""
        if data.empty:
            return
            
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Check if file exists and merge with existing data
        if file_path.exists():
            try:
                existing_data = pd.read_parquet(file_path)
                print(f"Merging new data ({len(data)} rows) with existing data ({len(existing_data)} rows)")
                
                # Combine and remove duplicates (keep the newer data)
                combined = pd.concat([existing_data, data]).sort_index()
                combined = combined[~combined.index.duplicated(keep='last')]
                
                print(f"Merged result: {len(combined)} rows from {combined.index.min().date()} to {combined.index.max().date()}")
                data = combined
            except Exception as e:
                print(f"Warning: Could not merge with existing data in {file_path}: {e}")
                print("Proceeding with overwrite...")
        
        try:
            data.to_parquet(file_path)
        except Exception as e:
            print(f"Error saving to {file_path}: {e}")
    
    def load_data(self, file_path: Path) -> Optional[pd.DataFrame]:
        """Load DataFrame from parquet file"""
        if not file_path.exists():
            return None
            
        try:
            return pd.read_parquet(file_path)
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            return None
    
    def download_raw_data(self, symbol: str, start_date: date, end_date: date, interval: str) -> pd.DataFrame:
        """Download raw data from Yahoo Finance"""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(start=start_date, end=end_date, interval=interval)
            
            if not data.empty:
                data.index.name = 'Date'
                
            return data
            
        except Exception as e:
            print(f"Error downloading {symbol}: {e}")
            return pd.DataFrame()
    
    def process_raw_data(self, raw_data: pd.DataFrame) -> pd.DataFrame:
        """
        Process raw data to create adjusted data
        For now, just copy raw data - can add split/dividend adjustments later
        """
        if raw_data.empty:
            return raw_data
        
        processed = raw_data.copy()
        
        # Add adjusted close (for now, same as close)
        # TODO: Implement proper dividend/split adjustments
        processed['Adj_Close'] = processed['Close']
        
        return processed
    
    def get_file_info(self, file_path: Path) -> dict:
        """Get file metadata"""
        if not file_path.exists():
            return {}
        
        try:
            data = pd.read_parquet(file_path)
            return {
                'row_count': len(data),
                'file_size': file_path.stat().st_size,
                'date_range': {
                    'start': str(data.index.min().date()) if not data.empty else None,
                    'end': str(data.index.max().date()) if not data.empty else None
                }
            }
        except:
            return {
                'file_size': file_path.stat().st_size
            }