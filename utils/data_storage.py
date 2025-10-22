"""
Data storage utilities for the pump.fun scraper
"""

import json
import csv
import sqlite3
import aiofiles
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import logging

from models import TokenInfo, TransactionData


class DataStorage:
    """
    Handles saving scraped data in various formats
    """
    
    def __init__(self, output_directory: str = "data"):
        self.output_dir = Path(output_directory)
        self.output_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        (self.output_dir / "tokens").mkdir(exist_ok=True)
        (self.output_dir / "transactions").mkdir(exist_ok=True)
        (self.output_dir / "launches").mkdir(exist_ok=True)
        (self.output_dir / "daily").mkdir(exist_ok=True)
        
        self.logger = logging.getLogger(__name__)
        
        # Initialize SQLite database
        self.db_path = self.output_dir / "pump_fun_data.db"
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database with tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Tokens table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    symbol TEXT,
                    price REAL,
                    market_cap REAL,
                    volume_24h REAL,
                    created_timestamp TIMESTAMP,
                    mint_address TEXT UNIQUE,
                    description TEXT,
                    image_uri TEXT,
                    twitter TEXT,
                    telegram TEXT,
                    website TEXT,
                    scraped_at TIMESTAMP,
                    UNIQUE(mint_address, scraped_at)
                )
            """)
            
            # Transactions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signature TEXT UNIQUE,
                    token_mint TEXT,
                    action TEXT,
                    amount REAL,
                    price REAL,
                    user_address TEXT,
                    timestamp TIMESTAMP,
                    scraped_at TIMESTAMP,
                    FOREIGN KEY (token_mint) REFERENCES tokens(mint_address)
                )
            """)
            
            # Create indexes for better performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tokens_symbol ON tokens(symbol)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tokens_created ON tokens(created_timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_mint ON transactions(token_mint)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_timestamp ON transactions(timestamp)")
            
            conn.commit()
            self.logger.info("Database initialized successfully")
    
    async def save_tokens(self, tokens: List[TokenInfo], format_type: str = "both"):
        """Save token data in specified format(s)"""
        if not tokens:
            self.logger.warning("No tokens to save")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            # Save to JSON
            if format_type in ["json", "both"]:
                await self._save_tokens_json(tokens, timestamp)
            
            # Save to CSV
            if format_type in ["csv", "both"]:
                await self._save_tokens_csv(tokens, timestamp)
            
            # Save to database
            await self._save_tokens_db(tokens)
            
            self.logger.info(f"Successfully saved {len(tokens)} tokens")
            
        except Exception as e:
            self.logger.error(f"Error saving tokens: {e}")
            raise
    
    async def save_transactions(self, transactions: List[TransactionData], format_type: str = "both"):
        """Save transaction data in specified format(s)"""
        if not transactions:
            self.logger.warning("No transactions to save")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            # Save to JSON
            if format_type in ["json", "both"]:
                await self._save_transactions_json(transactions, timestamp)
            
            # Save to CSV
            if format_type in ["csv", "both"]:
                await self._save_transactions_csv(transactions, timestamp)
            
            # Save to database
            await self._save_transactions_db(transactions)
            
            self.logger.info(f"Successfully saved {len(transactions)} transactions")
            
        except Exception as e:
            self.logger.error(f"Error saving transactions: {e}")
            raise
    
    async def save_new_launches(self, launches: List[TokenInfo], format_type: str = "both"):
        """Save new launch data"""
        if not launches:
            self.logger.warning("No new launches to save")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            # Save to JSON
            if format_type in ["json", "both"]:
                filename = self.output_dir / "launches" / f"new_launches_{timestamp}.json"
                data = [launch.model_dump(mode='json') for launch in launches]
                
                async with aiofiles.open(filename, "w") as f:
                    await f.write(json.dumps(data, indent=2, default=str))
            
            # Save to CSV
            if format_type in ["csv", "both"]:
                filename = self.output_dir / "launches" / f"new_launches_{timestamp}.csv"
                await self._write_csv(filename, launches, TokenInfo)
            
            self.logger.info(f"Successfully saved {len(launches)} new launches")
            
        except Exception as e:
            self.logger.error(f"Error saving new launches: {e}")
            raise
    
    async def _save_tokens_json(self, tokens: List[TokenInfo], timestamp: str):
        """Save tokens to JSON file"""
        filename = self.output_dir / "tokens" / f"tokens_{timestamp}.json"
        data = [token.model_dump(mode='json') for token in tokens]
        
        async with aiofiles.open(filename, "w") as f:
            await f.write(json.dumps(data, indent=2, default=str))
    
    async def _save_tokens_csv(self, tokens: List[TokenInfo], timestamp: str):
        """Save tokens to CSV file"""
        filename = self.output_dir / "tokens" / f"tokens_{timestamp}.csv"
        await self._write_csv(filename, tokens, TokenInfo)
    
    async def _save_transactions_json(self, transactions: List[TransactionData], timestamp: str):
        """Save transactions to JSON file"""
        filename = self.output_dir / "transactions" / f"transactions_{timestamp}.json"
        data = [tx.model_dump(mode='json') for tx in transactions]
        
        async with aiofiles.open(filename, "w") as f:
            await f.write(json.dumps(data, indent=2, default=str))
    
    async def _save_transactions_csv(self, transactions: List[TransactionData], timestamp: str):
        """Save transactions to CSV file"""
        filename = self.output_dir / "transactions" / f"transactions_{timestamp}.csv"
        await self._write_csv(filename, transactions, TransactionData)
    
    async def _save_tokens_db(self, tokens: List[TokenInfo]):
        """Save tokens to SQLite database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            for token in tokens:
                cursor.execute("""
                    INSERT OR REPLACE INTO tokens 
                    (name, symbol, price, market_cap, volume_24h, created_timestamp,
                     mint_address, description, image_uri, twitter, telegram, website, scraped_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    token.name, token.symbol, token.price, token.market_cap,
                    token.volume_24h, token.created_timestamp, token.mint_address,
                    token.description, token.image_uri, token.twitter,
                    token.telegram, token.website, token.scraped_at
                ))
            
            conn.commit()
    
    async def _save_transactions_db(self, transactions: List[TransactionData]):
        """Save transactions to SQLite database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            for tx in transactions:
                cursor.execute("""
                    INSERT OR IGNORE INTO transactions 
                    (signature, token_mint, action, amount, price, user_address, timestamp, scraped_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    tx.signature, tx.token_mint, tx.action, tx.amount,
                    tx.price, tx.user, tx.timestamp, tx.scraped_at
                ))
            
            conn.commit()
    
    async def _write_csv(self, filename: Path, data: List, model_class):
        """Generic CSV writer for Pydantic models"""
        if not data:
            return
        
        # Get field names from the first item
        fieldnames = list(data[0].model_dump().keys())
        
        with open(filename, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for item in data:
                row_data = item.model_dump()
                # Convert datetime objects to strings
                for key, value in row_data.items():
                    if isinstance(value, datetime):
                        row_data[key] = value.isoformat()
                writer.writerow(row_data)
    
    async def get_daily_summary(self, date: datetime = None) -> Dict[str, Any]:
        """Get daily summary statistics"""
        if date is None:
            date = datetime.now().date()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Token statistics
            cursor.execute("""
                SELECT COUNT(*) as token_count,
                       AVG(market_cap) as avg_market_cap,
                       SUM(volume_24h) as total_volume
                FROM tokens 
                WHERE DATE(scraped_at) = ?
            """, (date,))
            
            token_stats = cursor.fetchone()
            
            # Transaction statistics
            cursor.execute("""
                SELECT COUNT(*) as tx_count,
                       COUNT(DISTINCT token_mint) as unique_tokens,
                       SUM(CASE WHEN action = 'buy' THEN amount ELSE 0 END) as total_buys,
                       SUM(CASE WHEN action = 'sell' THEN amount ELSE 0 END) as total_sells
                FROM transactions 
                WHERE DATE(scraped_at) = ?
            """, (date,))
            
            tx_stats = cursor.fetchone()
            
            return {
                "date": date.isoformat(),
                "tokens": {
                    "count": token_stats[0] or 0,
                    "avg_market_cap": token_stats[1] or 0,
                    "total_volume": token_stats[2] or 0
                },
                "transactions": {
                    "count": tx_stats[0] or 0,
                    "unique_tokens": tx_stats[1] or 0,
                    "total_buys": tx_stats[2] or 0,
                    "total_sells": tx_stats[3] or 0
                }
            }
    
    async def export_data(self, start_date: datetime = None, end_date: datetime = None, format_type: str = "json"):
        """Export historical data within date range"""
        if start_date is None:
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        if end_date is None:
            end_date = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Export tokens
            cursor.execute("""
                SELECT * FROM tokens 
                WHERE scraped_at BETWEEN ? AND ?
                ORDER BY scraped_at DESC
            """, (start_date, end_date))
            
            tokens_data = cursor.fetchall()
            
            # Export transactions
            cursor.execute("""
                SELECT * FROM transactions 
                WHERE scraped_at BETWEEN ? AND ?
                ORDER BY scraped_at DESC
            """, (start_date, end_date))
            
            transactions_data = cursor.fetchall()
        
        # Save exported data
        export_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format_type == "json":
            export_data = {
                "export_timestamp": export_timestamp,
                "date_range": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                },
                "tokens": tokens_data,
                "transactions": transactions_data
            }
            
            filename = self.output_dir / f"export_{export_timestamp}.json"
            async with aiofiles.open(filename, "w") as f:
                await f.write(json.dumps(export_data, indent=2, default=str))
        
        self.logger.info(f"Exported data to {filename}")
        return str(filename)