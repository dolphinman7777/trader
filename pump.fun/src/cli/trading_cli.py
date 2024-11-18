import asyncio
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from datetime import datetime
from typing import Dict, List
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import DatabaseManager
from utils.logger import TradingLogger

class TradingCLI:
    def __init__(self):
        self.console = Console()
        self.db = DatabaseManager()
        self.logger = TradingLogger()
        self.active_trades: List[Dict] = []
        self.recent_tweets: List[Dict] = []
        self.performance_summary: Dict = {}

    def generate_layout(self) -> Layout:
        layout = Layout()
        
        layout.split(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1)
        )
        
        layout["main"].split_row(
            Layout(name="left"),
            Layout(name="right")
        )
        
        layout["left"].split(
            Layout(name="active_trades"),
            Layout(name="recent_tweets")
        )
        
        layout["right"].split(
            Layout(name="performance"),
            Layout(name="logs")
        )
        
        return layout

    def generate_header(self) -> Panel:
        grid = Table.grid(expand=True)
        grid.add_column(justify="center", ratio=1)
        grid.add_row("🤖 Solana Trading Bot")
        
        return Panel(
            grid,
            style="white on blue",
            padding=(0, 2)
        )

    def generate_active_trades_table(self) -> Table:
        table = Table(title="Active Trades", expand=True)
        table.add_column("Token")
        table.add_column("Amount")
        table.add_column("Entry Price")
        table.add_column("Current Price")
        table.add_column("P/L %")
        
        for trade in self.active_trades:
            pl_pct = ((trade.get('current_price', 0) - trade['entry_price']) 
                     / trade['entry_price'] * 100)
            color = "green" if pl_pct > 0 else "red"
            
            table.add_row(
                trade['token_symbol'],
                f"{trade['amount']:.3f}",
                f"{trade['entry_price']:.4f}",
                f"{trade.get('current_price', 0):.4f}",
                Text(f"{pl_pct:+.2f}%", style=color)
            )
        
        return table

    def generate_recent_tweets_table(self) -> Table:
        table = Table(title="Recent Tweets", expand=True)
        table.add_column("Time")
        table.add_column("Author")
        table.add_column("Tweet")
        
        for tweet in self.recent_tweets[-5:]:  # Show last 5 tweets
            table.add_row(
                tweet['created_at'].strftime("%H:%M:%S"),
                tweet['author_id'],
                Text(tweet['text'][:50] + "..." if len(tweet['text']) > 50 else tweet['text'])
            )
        
        return table

    def generate_performance_panel(self) -> Panel:
        content = Table.grid(padding=1)
        content.add_column("Metric")
        content.add_column("Value")
        
        metrics = [
            ("Total Trades", str(self.performance_summary.get('total_trades', 0))),
            ("Win Rate", f"{self.performance_summary.get('win_rate', 0)*100:.1f}%"),
            ("Total Profit", f"{self.performance_summary.get('total_profit', 0):.3f} SOL"),
            ("Avg Profit/Trade", f"{self.performance_summary.get('avg_profit_per_trade', 0):.3f} SOL")
        ]
        
        for metric, value in metrics:
            content.add_row(metric, value)
        
        return Panel(content, title="Performance")

    def generate_log_panel(self) -> Panel:
        # Get last few log entries
        with open(self.logger.logger.handlers[0].baseFilename, 'r') as f:
            logs = f.readlines()[-10:]  # Last 10 log entries
        
        return Panel(
            "\n".join(logs),
            title="Recent Logs",
            height=15
        )

    async def update_data(self):
        while True:
            try:
                # Update active trades
                self.active_trades = await self.db.get_active_trades()
                
                # Update performance summary
                self.performance_summary = await self.db.get_performance_summary()
                
                await asyncio.sleep(5)  # Update every 5 seconds
                
            except Exception as e:
                self.logger.log_error(f"Error updating CLI data: {e}")
                await asyncio.sleep(5)

    def update_display(self, layout: Layout) -> None:
        try:
            # Update each component
            layout["header"].update(self.generate_header())
            layout["active_trades"].update(self.generate_active_trades_table())
            layout["recent_tweets"].update(self.generate_recent_tweets_table())
            layout["performance"].update(self.generate_performance_panel())
            layout["logs"].update(self.generate_log_panel())
            
        except Exception as e:
            self.logger.log_error(f"Error updating display: {e}")

    async def run(self):
        layout = self.generate_layout()
        
        # Start data update task
        asyncio.create_task(self.update_data())
        
        with Live(layout, refresh_per_second=1, screen=True):
            while True:
                self.update_display(layout)
                await asyncio.sleep(1)

def main():
    cli = TradingCLI()
    asyncio.run(cli.run())

if __name__ == "__main__":
    main() 