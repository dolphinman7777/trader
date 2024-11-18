import sqlite3
from datetime import datetime
import os
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Trade:
    id: Optional[int]
    token_address: str
    token_symbol: str
    action: str
    amount: float
    price: float
    timestamp: datetime
    tweet_id: str
    confidence: float
    status: str  # 'pending', 'completed', 'failed'
    profit_loss: Optional[float] = None

class DatabaseManager:
    def __init__(self, db_path: str = "trading_bot.db"):
        self.db_path = db_path
        self._create_tables()

    def _create_tables(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create trades table with a proper unique constraint
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_address TEXT NOT NULL,
                token_symbol TEXT NOT NULL,
                action TEXT NOT NULL,
                amount REAL NOT NULL,
                price REAL NOT NULL,
                timestamp DATETIME NOT NULL,
                tweet_id TEXT NOT NULL,
                confidence REAL NOT NULL,
                status TEXT NOT NULL,
                profit_loss REAL
            )
        ''')

        # Create performance metrics table with date as unique key
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE UNIQUE NOT NULL,
                total_trades INTEGER NOT NULL,
                successful_trades INTEGER NOT NULL,
                total_profit_loss REAL NOT NULL,
                win_rate REAL NOT NULL
            )
        ''')

        conn.commit()
        conn.close()

    async def record_trade(self, trade: Trade) -> int:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO trades (
                token_address, token_symbol, action, amount, 
                price, timestamp, tweet_id, confidence, status, profit_loss
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            trade.token_address, trade.token_symbol, trade.action,
            trade.amount, trade.price, trade.timestamp.isoformat(),
            trade.tweet_id, trade.confidence, trade.status, trade.profit_loss
        ))

        trade_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return trade_id

    async def update_trade_status(self, trade_id: int, status: str, profit_loss: Optional[float] = None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if profit_loss is not None:
            cursor.execute('''
                UPDATE trades 
                SET status = ?, profit_loss = ?
                WHERE id = ?
            ''', (status, profit_loss, trade_id))
        else:
            cursor.execute('''
                UPDATE trades 
                SET status = ?
                WHERE id = ?
            ''', (status, trade_id))

        conn.commit()
        conn.close()

    async def get_active_trades(self) -> List[Trade]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM trades 
            WHERE status = 'pending'
        ''')

        trades = []
        for row in cursor.fetchall():
            trades.append(Trade(
                id=row[0],
                token_address=row[1],
                token_symbol=row[2],
                action=row[3],
                amount=row[4],
                price=row[5],
                timestamp=datetime.fromisoformat(row[6]),
                tweet_id=row[7],
                confidence=row[8],
                status=row[9],
                profit_loss=row[10]
            ))

        conn.close()
        return trades

    async def update_performance_metrics(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Calculate daily performance metrics
        cursor.execute('''
            INSERT OR REPLACE INTO performance_metrics (
                date, total_trades, successful_trades, 
                total_profit_loss, win_rate
            )
            SELECT 
                DATE(timestamp) as date,
                COUNT(*) as total_trades,
                SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as successful_trades,
                SUM(COALESCE(profit_loss, 0)) as total_profit_loss,
                CAST(SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) AS FLOAT) / 
                    NULLIF(COUNT(*), 0) as win_rate
            FROM trades
            WHERE status = 'completed'
            GROUP BY DATE(timestamp)
        ''')

        conn.commit()
        conn.close()

    async def get_performance_summary(self) -> dict:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT 
                COUNT(*) as total_trades,
                SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades,
                SUM(COALESCE(profit_loss, 0)) as total_profit,
                AVG(COALESCE(profit_loss, 0)) as avg_profit_per_trade
            FROM trades
            WHERE status = 'completed'
        ''')

        row = cursor.fetchone()
        total_trades = row[0] or 0
        winning_trades = row[1] or 0
        
        summary = {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'total_profit': row[2] or 0,
            'avg_profit_per_trade': row[3] or 0,
            'win_rate': winning_trades / total_trades if total_trades > 0 else 0
        }

        conn.close()
        return summary 

    async def record_trade_metrics(self, trade_id: int, exit_price: float):
        """Record detailed metrics for completed trade"""
        # Calculate metrics
        trade = await self.get_trade(trade_id)
        pl_amount = (exit_price - trade.price) * trade.amount
        pl_percentage = (exit_price - trade.price) / trade.price * 100
        
        # Store in database
        # ... implementation 