# core/data_engine/metadata.py
import sqlite3
from datetime import date
from pathlib import Path
from typing import List, Dict

class MetadataStore:
    """
    Manages metadata database for tracking data files and symbols
    """
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS symbols (
                    symbol TEXT PRIMARY KEY,
                    name TEXT,
                    sector TEXT,
                    market_cap REAL,
                    asset_type TEXT CHECK(asset_type IN ('stock', 'crypto')),
                    active BOOLEAN DEFAULT TRUE,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS data_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    interval TEXT NOT NULL,
                    data_type TEXT CHECK(data_type IN ('raw', 'processed', 'cache')),
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    file_path TEXT NOT NULL,
                    row_count INTEGER,
                    file_size INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (symbol) REFERENCES symbols (symbol)
                );
                
                CREATE INDEX IF NOT EXISTS idx_data_files_symbol ON data_files(symbol);
                CREATE INDEX IF NOT EXISTS idx_data_files_dates ON data_files(start_date, end_date);
                CREATE INDEX IF NOT EXISTS idx_data_files_type ON data_files(data_type);
            """)
    
    def add_symbol(self, symbol: str, name: str = None, sector: str = None, 
                   market_cap: float = None, asset_type: str = None):
        """Add or update symbol metadata"""
        if asset_type is None:
            asset_type = 'crypto' if '-USD' in symbol else 'stock'
            
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO symbols 
                (symbol, name, sector, market_cap, asset_type, last_updated)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (symbol, name, sector, market_cap, asset_type))
    
    def register_data_file(self, symbol: str, interval: str, data_type: str,
                          start_date: date, end_date: date, file_path: str,
                          row_count: int = None, file_size: int = None):
        """Register a data file in the metadata, updating existing entries for the same file path"""
        with sqlite3.connect(self.db_path) as conn:
            # First, delete any existing entries for this exact file path
            # This handles the case where we're updating merged data
            conn.execute("""
                DELETE FROM data_files 
                WHERE file_path = ?
            """, (file_path,))
            
            # Then insert the new/updated entry
            conn.execute("""
                INSERT INTO data_files 
                (symbol, interval, data_type, start_date, end_date, file_path, row_count, file_size)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (symbol, interval, data_type, start_date, end_date, file_path, row_count, file_size))
    
    def get_data_files(self, symbol: str, interval: str, data_type: str,
                      start_date: date = None, end_date: date = None) -> List[Dict]:
        """Get available data files for symbol"""
        query = """
            SELECT symbol, interval, data_type, start_date, end_date, file_path, row_count, file_size
            FROM data_files 
            WHERE symbol = ? AND interval = ? AND data_type = ?
        """
        params = [symbol, interval, data_type]
        
        if start_date:
            query += " AND end_date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND start_date <= ?"
            params.append(end_date)
            
        query += " ORDER BY start_date"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_symbols(self, asset_type: str = None, active: bool = True) -> List[Dict]:
        """Get list of symbols"""
        query = "SELECT * FROM symbols WHERE active = ?"
        params = [active]
        
        if asset_type:
            query += " AND asset_type = ?"
            params.append(asset_type)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_data_coverage(self, symbol: str, interval: str) -> Dict:
        """Get data coverage summary for symbol"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT data_type, MIN(start_date) as earliest, MAX(end_date) as latest, 
                       COUNT(*) as file_count, SUM(row_count) as total_rows
                FROM data_files 
                WHERE symbol = ? AND interval = ?
                GROUP BY data_type
            """, (symbol, interval))
            
            coverage = {}
            for row in cursor:
                coverage[row['data_type']] = {
                    'earliest': row['earliest'],
                    'latest': row['latest'], 
                    'file_count': row['file_count'],
                    'total_rows': row['total_rows']
                }
            return coverage