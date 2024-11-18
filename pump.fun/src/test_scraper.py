import asyncio
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt
from rich.live import Live
from dotenv import load_dotenv
from social.twitter_scanner import TwitterScanner
import time

console = Console()

class ScraperTester:
    def __init__(self):
        self.scanner = TwitterScanner()
        self.monitoring = False

    async def test_all_domains(self):
        """Test each scraping domain individually"""
        for domain in self.scanner.domains:
            console.print(f"\n[yellow]Testing {domain}...[/yellow]")
            try:
                tweets = await self.scanner._scrape_tweets(domain)
                if tweets:
                    console.print(f"[green]✓ Found {len(tweets)} tweets from {domain}[/green]")
                    self.display_tweets(tweets)
                else:
                    console.print(f"[red]✗ No tweets found from {domain}[/red]")
            except Exception as e:
                console.print(f"[red]Error with {domain}: {str(e)}[/red]")

    async def monitor_live(self):
        """Monitor tweets in real-time with live updates"""
        with Live(self.generate_display(), refresh_per_second=1) as live:
            self.monitoring = True
            while self.monitoring:
                try:
                    tweets = await self.scanner.get_relevant_tweets()
                    if tweets:
                        live.update(self.generate_display(tweets))
                    await asyncio.sleep(5)
                except KeyboardInterrupt:
                    self.monitoring = False
                except Exception as e:
                    console.print(f"[red]Error: {str(e)}[/red]")
                    await asyncio.sleep(30)

    def generate_display(self, tweets=None) -> Panel:
        """Generate display panel for tweets"""
        table = Table(title="Latest Tweets from @ecca")
        table.add_column("Time", style="cyan", width=10)
        table.add_column("Text", style="white", width=50)
        table.add_column("Source", style="green", width=10)
        table.add_column("Metrics", style="yellow", width=20)

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
                    tweet.get('source', 'unknown'),
                    metrics_str
                )

        return Panel(table, title="Tweet Monitor", border_style="blue")

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
            console.print("1. Test all scraping domains")
            console.print("2. Monitor tweets in real-time")
            console.print("3. Test single domain")
            console.print("4. Exit")
            
            choice = Prompt.ask("Select option", choices=["1", "2", "3", "4"])
            
            if choice == "1":
                await self.test_all_domains()
            elif choice == "2":
                console.print("[yellow]Starting tweet monitor (Press Ctrl+C to stop)...[/yellow]")
                await self.monitor_live()
            elif choice == "3":
                domains = {str(i): d for i, d in enumerate(self.scanner.domains, 1)}
                for num, domain in domains.items():
                    console.print(f"{num}. {domain}")
                domain_choice = Prompt.ask("Select domain", choices=list(domains.keys()))
                domain = domains[domain_choice]
                tweets = await self.scanner._scrape_tweets(domain)
                if tweets:
                    self.display_tweets(tweets)
                else:
                    console.print(f"[red]No tweets found from {domain}[/red]")
            else:
                break

async def main():
    load_dotenv()
    tester = ScraperTester()
    await tester.run()

if __name__ == "__main__":
    asyncio.run(main()) 