import asyncio
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich.live import Live
from dotenv import load_dotenv
from social.twitter_scanner import TwitterScanner
import time

console = Console()

class TwitterTestCLI:
    def __init__(self):
        self.scanner = TwitterScanner()
        self.monitoring = False

    async def monitor_tweets(self):
        """Monitor tweets in real-time with live updates"""
        with Live(self.generate_display(), refresh_per_second=1) as live:
            self.monitoring = True
            while self.monitoring:
                try:
                    tweets = await self.scanner.get_relevant_tweets()
                    if tweets:
                        live.update(self.generate_display(tweets))
                    await asyncio.sleep(5)  # Check every 5 seconds
                except KeyboardInterrupt:
                    self.monitoring = False
                except Exception as e:
                    console.print(f"[red]Error: {str(e)}[/red]")
                    await asyncio.sleep(30)

    def generate_display(self, tweets=None) -> Panel:
        """Generate display panel for tweets"""
        table = Table(title="Latest Tweets from @ecca")
        table.add_column("Time", style="cyan")
        table.add_column("Text", style="white")
        table.add_column("Metrics", style="green")

        if tweets:
            for tweet in tweets:
                metrics = tweet.get('metrics', {})
                metrics_str = (
                    f"♥ {metrics.get('like_count', 0)} "
                    f"🔄 {metrics.get('retweet_count', 0)} "
                    f"💬 {metrics.get('reply_count', 0)}"
                )
                table.add_row(
                    tweet['created_at'].strftime("%H:%M:%S"),
                    tweet['text'][:100] + "..." if len(tweet['text']) > 100 else tweet['text'],
                    metrics_str
                )

        return Panel(table, title="Tweet Monitor", border_style="blue")

    async def test_api(self):
        """Test Twitter API connection"""
        console.print("[yellow]Testing Twitter API...[/yellow]")
        try:
            tweets = await self.scanner._get_tweets_api()
            if tweets:
                console.print(f"[green]✓ Successfully fetched {len(tweets)} tweets via API[/green]")
                self.display_tweets(tweets)
            else:
                console.print("[red]✗ No tweets found via API[/red]")
        except Exception as e:
            console.print(f"[red]✗ API Error: {str(e)}[/red]")

    async def test_web_scraping(self):
        """Test web scraping fallback"""
        console.print("[yellow]Testing web scraping...[/yellow]")
        try:
            tweets = await self.scanner._get_tweets_web()
            if tweets:
                console.print(f"[green]✓ Successfully fetched {len(tweets)} tweets via web scraping[/green]")
                self.display_tweets(tweets)
            else:
                console.print("[red]✗ No tweets found via web scraping[/red]")
        except Exception as e:
            console.print(f"[red]✗ Scraping Error: {str(e)}[/red]")

    def display_tweets(self, tweets):
        """Display tweets in a table"""
        table = Table(title="Tweets")
        table.add_column("Time", style="cyan")
        table.add_column("Text", style="white", no_wrap=False)
        table.add_column("Metrics", style="green")

        for tweet in tweets:
            metrics = tweet.get('metrics', {})
            metrics_str = (
                f"♥ {metrics.get('like_count', 0)} "
                f"🔄 {metrics.get('retweet_count', 0)} "
                f"💬 {metrics.get('reply_count', 0)}"
            )
            table.add_row(
                tweet['created_at'].strftime("%Y-%m-%d %H:%M:%S"),
                tweet['text'],
                metrics_str
            )

        console.print(table)

    async def run(self):
        while True:
            console.print("\n[bold cyan]Available commands:[/bold cyan]")
            console.print("1. Monitor tweets in real-time")
            console.print("2. Test Twitter API")
            console.print("3. Test web scraping")
            console.print("4. Exit")
            
            choice = Prompt.ask("Select option", choices=["1", "2", "3", "4"])
            
            if choice == "1":
                console.print("[yellow]Starting tweet monitor (Press Ctrl+C to stop)...[/yellow]")
                await self.monitor_tweets()
            elif choice == "2":
                await self.test_api()
            elif choice == "3":
                await self.test_web_scraping()
            else:
                break

async def main():
    load_dotenv()
    cli = TwitterTestCLI()
    await cli.run()

if __name__ == "__main__":
    asyncio.run(main()) 