import asyncio
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.layout import Layout
from rich.prompt import Prompt
from rich.status import Status
from rich.text import Text
from rich.progress import Progress, SpinnerColumn
from social.twitter_scanner import TwitterScanner
from blockchain.solana_client import SolanaClient
from datetime import datetime, timedelta
from collections import deque

console = Console()

class TokenScanner:
    def __init__(self):
        self.twitter_scanner = TwitterScanner()
        self.solana_client = SolanaClient()
        self.trending_tokens = {}
        self.token_prices = {}
        self.status_messages = deque(maxlen=10)
        self.last_update = datetime.now()
        self.scan_count = 0

    def generate_display(self) -> Layout:
        """Generate display with trending tokens and status"""
        layout = Layout()
        layout.split_column(
            Layout(name="stats", size=3),
            Layout(name="main"),
            Layout(name="status", size=12)
        )

        # Stats panel showing scan info
        stats_table = Table.grid(padding=1)
        stats_table.add_column(style="cyan")
        stats_table.add_column(style="green")
        stats_table.add_column(style="yellow")
        stats_table.add_row(
            f"Scans: {self.scan_count}",
            f"Tokens Found: {len(self.trending_tokens)}",
            f"Last Update: {self.last_update.strftime('%H:%M:%S')}"
        )
        
        # Trending tokens table
        trending_table = Table(title="🔥 Trending Tokens")
        trending_table.add_column("Token", style="cyan", width=12)
        trending_table.add_column("Score", justify="right", style="green", width=8)
        trending_table.add_column("24h Mentions", justify="right", width=10)
        trending_table.add_column("1h Velocity", justify="right", width=10)
        trending_table.add_column("Engagement", justify="right", width=10)
        trending_table.add_column("Sentiment", justify="right", width=10)
        trending_table.add_column("Age", justify="right", width=10)
        trending_table.add_column("Signals", width=15)

        # Sort tokens by trend score
        current_time = datetime.now()
        sorted_tokens = sorted(
            [(k, v) for k, v in self.trending_tokens.items()],
            key=lambda x: x[1]['trend_score'],
            reverse=True
        )

        # Add top 20 tokens to table
        for token, data in sorted_tokens[:20]:
            age = current_time - data['first_seen']
            age_str = f"{age.seconds // 3600}h {(age.seconds % 3600) // 60}m"
            
            # Calculate signals
            signals = []
            if data['velocity'] >= 5:
                signals.append("🔥")  # Hot velocity
            if data['engagement'] / max(data['mention_count'], 1) >= 100:
                signals.append("⭐")  # High engagement
            if data['avg_sentiment'] >= 0.5:
                signals.append("📈")  # Positive sentiment
            if len(data['unique_users']) / max(data['mention_count'], 1) >= 0.8:
                signals.append("👥")  # Unique users ratio
            
            trending_table.add_row(
                token,
                f"{data['trend_score']:.2f}",
                str(data['mention_count']),
                f"{data['velocity']:.1f}/h",
                f"{data['engagement']:.0f}",
                f"{data['avg_sentiment']:.2f}",
                age_str,
                " ".join(signals)
            )

        # Status panel
        status_table = Table(show_header=False, show_edge=False, pad_edge=False)
        status_table.add_column("Time", style="bright_black", width=10)
        status_table.add_column("Status")

        for msg in self.status_messages:
            status_table.add_row(
                msg['time'].strftime("%H:%M:%S"),
                Text(msg['text'], style=msg['style'])
            )

        # Add all components to layout
        layout["stats"].update(Panel(stats_table, title="Scanner Stats"))
        layout["main"].update(Panel(trending_table, title="Trending Tokens"))
        layout["status"].update(Panel(status_table, title="Scanner Status"))

        return layout

    def add_status(self, message: str, style: str = "white"):
        """Add a status message to the log"""
        self.status_messages.append({
            'time': datetime.now(),
            'text': message,
            'style': style
        })

    async def monitor(self):
        """Monitor trending tokens"""
        with Live(self.generate_display(), refresh_per_second=1) as live:
            while True:
                try:
                    self.scan_count += 1
                    self.add_status("Starting new scan...", "yellow")
                    
                    # Get trending tokens
                    trending = await self.twitter_scanner.search_trending_tokens()
                    
                    if trending:
                        self.trending_tokens = trending
                        self.add_status(
                            f"Found {len(trending)} trending tokens", 
                            "green"
                        )
                        
                        # Show top 5 tokens in status
                        top_tokens = list(trending.items())[:5]
                        for token, data in top_tokens:
                            self.add_status(
                                f"🔥 {token}: score={data['trend_score']:.2f}, "
                                f"mentions={data['mention_count']}, "
                                f"velocity={data['velocity']:.1f}/h",
                                "cyan"
                            )
                    else:
                        self.add_status("No trending tokens found", "red")
                    
                    self.last_update = datetime.now()
                    live.update(self.generate_display())
                    
                    # Show countdown
                    for i in range(30, 0, -1):
                        self.add_status(f"Next scan in {i}s...", "blue")
                        live.update(self.generate_display())
                        await asyncio.sleep(1)
                    
                except KeyboardInterrupt:
                    self.add_status("Scanner stopped by user", "yellow")
                    break
                except Exception as e:
                    self.add_status(f"Error: {str(e)}", "red")
                    await asyncio.sleep(60)

    async def update_prices(self):
        """Update prices for trending tokens"""
        for token, data in self.trending_tokens.items():
            if addresses := data.get('addresses', []):
                for address in addresses:
                    if price := await self.solana_client.get_token_price(address):
                        self.token_prices[token] = price
                        self.add_status(f"Updated price for {token}: ${price}", "green")
                        break

async def main():
    load_dotenv()
    scanner = TokenScanner()
    await scanner.monitor()

if __name__ == "__main__":
    asyncio.run(main()) 