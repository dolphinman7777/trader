from blockchain.solana_client import SolanaClient
from database.db_manager import DatabaseManager, Trade
from typing import Dict
import os
from datetime import datetime
import asyncio

class PumpTrader:
    def __init__(self, solana_client: SolanaClient):
        self.solana_client = solana_client
        self.db = DatabaseManager()
        self.max_trade_amount = float(os.getenv('MAX_TRADE_AMOUNT', '0.1'))
        self.stop_loss_percentage = float(os.getenv('STOP_LOSS_PERCENTAGE', '0.1'))
        self.take_profit_percentage = float(os.getenv('TAKE_PROFIT_PERCENTAGE', '0.3'))
        
        # Track active trades
        self.active_trades: Dict[str, Dict] = {}

    async def execute_trade(self, token_address: str, action: str, amount: float, 
                          tweet_id: str, confidence: float, token_symbol: str):
        try:
            if action == 'buy' and amount <= self.max_trade_amount:
                # Get current price
                price = await self.solana_client.get_token_price(token_address)
                if not price:
                    return False

                # Record trade in database
                trade = Trade(
                    id=None,
                    token_address=token_address,
                    token_symbol=token_symbol,
                    action=action,
                    amount=amount,
                    price=price,
                    timestamp=datetime.now(),
                    tweet_id=tweet_id,
                    confidence=confidence,
                    status='pending'
                )
                
                trade_id = await self.db.record_trade(trade)

                # Execute buy
                success = await self._execute_buy(token_address, amount)
                
                if success:
                    await self.db.update_trade_status(trade_id, 'completed')
                    # Set up monitoring for this position
                    await self._monitor_position(token_address, amount, trade_id)
                else:
                    await self.db.update_trade_status(trade_id, 'failed')
                
                return success
            
            elif action == 'sell' and token_address in self.active_trades:
                return await self._execute_sell(token_address)
                
        except Exception as e:
            print(f"Error executing trade: {e}")
            return False

    async def _execute_buy(self, token_address: str, amount: float) -> bool:
        # Get current price
        entry_price = await self.solana_client.get_token_price(token_address)
        if not entry_price:
            return False

        # Execute swap from SOL to token
        success = await self.solana_client.execute_swap(
            "SOL",  # Native SOL
            token_address,
            amount
        )

        if success:
            self.active_trades[token_address] = {
                'entry_price': entry_price,
                'amount': amount,
                'stop_loss': entry_price * (1 - self.stop_loss_percentage),
                'take_profit': entry_price * (1 + self.take_profit_percentage)
            }
            
        return success

    async def _execute_sell(self, token_address: str) -> bool:
        if token_address not in self.active_trades:
            return False

        trade = self.active_trades[token_address]
        
        # Swap back to SOL
        success = await self.solana_client.execute_swap(
            token_address,
            "SOL",  # Native SOL
            trade['amount']
        )

        if success:
            del self.active_trades[token_address]

        return success

    async def _monitor_position(self, token_address: str, amount: float, trade_id: int):
        """
        Monitor position for stop loss and take profit
        This should be run in a separate task
        """
        trade = self.active_trades.get(token_address)
        if not trade:
            return

        current_price = await self.solana_client.get_token_price(token_address)
        
        if current_price <= trade['stop_loss'] or current_price >= trade['take_profit']:
            await self._execute_sell(token_address)
            await self.db.update_trade_status(trade_id, 'failed')

    async def manage_positions(self):
        """Monitor and manage all open positions"""
        while True:
            for token_address, position in self.active_trades.items():
                current_price = await self.solana_client.get_token_price(token_address)
                if not current_price:
                    continue
                
                # Calculate P/L
                pl_pct = (current_price - position['entry_price']) / position['entry_price']
                
                # Check stop loss and take profit
                if pl_pct <= -self.stop_loss_percentage or pl_pct >= self.take_profit_percentage:
                    await self._execute_sell(token_address)
                
            await asyncio.sleep(5)  # Check every 5 seconds
  