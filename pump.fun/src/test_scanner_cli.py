import asyncio
import click
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from datetime import datetime

from social.twitter_scanner import TwitterScanner
from social.sentiment_scanner import SentimentScanner
from test_token_scanner import TokenScanner

console = Console()

class ScannerTester:
    def __init__(self):
        self.twitter_scanner = TwitterScanner()
        self.sentiment_scanner = SentimentScanner()
        self.token_scanner = TokenScanner()
        self.scan_count = 0
        self.last_update = None
        self.trending_tokens = []

    def generate_display(self):
        """Generate display table"""
        table = Table(title="🔥 Trending Tokens")
        
        table.add_column("Token", style="cyan")
        table.add_column("Score", justify="right", style="green")
        table.add_column("Mentions", justify="right")
        table.add_column("Engagement", justify="right")
        table.add_column("Velocity", justify="right", style="yellow")

        for token in self.trending_tokens:
            table.add_row(
                f"${token['token']}", 
                f"{token['trend_score']:.2f}",
                str(token['mentions']),
                f"{token['engagement']:.0f}",
                f"{token['velocity']:.1f}x"
            )

        return table

    async def monitor(self):
        """Monitor trending tokens"""
        console.print("[bold]Starting Token Monitor[/bold]")
        console.print("[yellow]Press Ctrl+C to stop monitoring[/yellow]\n")

        with Live(self.generate_display(), refresh_per_second=1) as live:
            while True:
                try:
                    self.scan_count += 1
                    trending = await self.twitter_scanner.search_trending_tokens()
                    
                    if trending:
                        self.trending_tokens = trending
                        self.last_update = datetime.now()
                        live.update(self.generate_display())
                    
                    await asyncio.sleep(30)  # Update every 30 seconds
                    
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    console.print(f"[red]Error: {str(e)}[/red]")
                    await asyncio.sleep(5)

    async def test_search_functionality(self):
        """Test search functionality"""
        console.print("\n[bold]Testing Search Functionality[/bold]")
        
        custom_query = Prompt.ask(
            "\nEnter custom search query (or press enter for default)",
            default="($SOL OR $BONK) lang:en"
        )
        
        self.twitter_scanner.search_queries = [custom_query]
        
        with console.status("[bold green]Searching Twitter...") as status:
            trending = await self.twitter_scanner.search_trending_tokens()
            
            if trending:
                table = Table(title="Search Results")
                table.add_column("Token")
                table.add_column("Score", justify="right")
                table.add_column("Mentions", justify="right")
                table.add_column("Sentiment", justify="right")
                table.add_column("Risk", justify="right", style="red")
                
                for token, data in trending.items():
                    table.add_row(
                        token,
                        f"{data['trend_score']:.2f}",
                        str(data['mention_count']),
                        f"{data['avg_sentiment']:.2f}",
                        f"{data.get('risk_score', 0):.2f}"
                    )
                
                console.print(table)
            else:
                console.print("[yellow]No results found[/yellow]")

    async def test_token_detection(self):
        """Test token detection patterns"""
        console.print("\n[bold]Testing Token Detection[/bold]")
        
        test_tweets = [
            "Just bought $SOL at $234!",
            "New token alert: BWgGBH5X2LsFQarTiLtmZwBzPwuV1pcbMTLcURycpump",
            "$BONK/SOL pair looking good",
            "Check out test.pump for more info",
            "@token_pump is pumping!",
            "$WEN moon? 🚀",
            "Aped into $MYRO at 0.5",
            "New gem $ABC launching soon!",
            "$XYZ/SOL LP growing fast",
            "$DEF.pump contract"
        ]
        
        for tweet in test_tweets:
            console.print(f"\nTesting tweet: {tweet}")
            tokens = self.sentiment_scanner._extract_token_info(tweet)
            if tokens:
                console.print(Panel(
                    "\n".join([f"Token: {t['symbol']} ({t['type']})" for t in tokens]),
                    title="Detected Tokens",
                    style="green"
                ))
            else:
                console.print("[yellow]No tokens detected[/yellow]")

    async def test_sentiment_analysis(self):
        """Test sentiment analysis"""
        console.print("\n[bold]Testing Sentiment Analysis[/bold]")
        
        test_tweets = [
            "🚀 $SOL to the moon! Price target $500 EOY",
            "⚠️ Be careful with $SCAM, looks suspicious",
            "$GEM 100x potential, early gem! 💎",
            "Dumping my $TOKEN, project looks dead 📉",
            "$LAUNCH presale starting in 1 hour! Don't miss 🔥"
        ]
        
        table = Table(title="Sentiment Analysis Results")
        table.add_column("Tweet")
        table.add_column("Sentiment", justify="right")
        table.add_column("Signals")
        
        for tweet in test_tweets:
            sentiment = self.sentiment_scanner._calculate_advanced_sentiment(tweet)
            signals = []
            if sentiment['emoji_sentiment'] != 0:
                signals.append("Emoji")
            if sentiment['price_targets']:
                signals.append("Price Target")
            if sentiment['urgency'] > 0:
                signals.append("Urgency")
                
            table.add_row(
                tweet,
                f"{sentiment['sentiment']:.2f}",
                ", ".join(signals)
            )
        
        console.print(table)

@click.command()
def main():
    """Token Scanner Test Suite"""
    console.print("\n[bold]Scanner Test Suite[/bold]\n")
    
    tests = {
        "1": ("Monitor tokens in real-time", "monitor"),
        "2": ("Test search functionality", "test_search_functionality"),
        "3": ("Test token detection", "test_token_detection"),
        "4": ("Test sentiment analysis", "test_sentiment_analysis"),
        "5": ("Exit", None)
    }
    
    # Display available tests
    console.print("Available tests:")
    for key, (name, _) in tests.items():
        console.print(f"{key}. {name}")
    
    while True:
        choice = Prompt.ask(
            "Select test",
            choices=list(tests.keys()),
            default="1"
        )
        
        if choice == "5":
            break
            
        test_name = tests[choice][1]
        tester = ScannerTester()
        
        try:
            asyncio.run(getattr(tester, test_name)())
        except Exception as e:
            console.print(f"[red]Error running test: {str(e)}[/red]")
        
        if choice != "1":  # Don't prompt after live monitoring (requires Ctrl+C)
            if not Prompt.ask("\nRun another test?", choices=["y", "n"], default="y") == "y":
                break

if __name__ == "__main__":
    main() 