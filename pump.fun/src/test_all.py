import asyncio
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from dotenv import load_dotenv

from social.twitter_scanner import TwitterScanner
from social.target_scanner import TargetScanner
from social.sentiment_scanner import SentimentScanner
from ai.ollama_client import OllamaClient
from blockchain.solana_client import SolanaClient

console = Console()

class ComponentTester:
    def __init__(self):
        self.twitter = TwitterScanner()
        self.target = TargetScanner()
        self.sentiment = SentimentScanner()
        self.ollama = OllamaClient(model="dolphin-mistral")
        self.solana = SolanaClient()

    async def test_twitter_scraping(self):
        """Test direct Twitter scraping"""
        console.print("\n[bold blue]Testing Twitter Scraping...[/bold blue]")
        try:
            tweets = await self.twitter.get_relevant_tweets()
            if tweets:
                console.print(f"[green]✓ Found {len(tweets)} tweets from @ecca[/green]")
                for tweet in tweets[:5]:  # Show first 5 tweets
                    console.print(Panel(
                        f"Time: {tweet['created_at']}\n"
                        f"Text: {tweet['text']}\n"
                        f"Metrics: {tweet['metrics']}",
                        title="Tweet"
                    ))
            else:
                console.print("[red]✗ No tweets found[/red]")
        except Exception as e:
            console.print(f"[red]Error in Twitter scraping: {str(e)}[/red]")

    async def test_target_monitoring(self):
        """Test target account monitoring"""
        console.print("\n[bold blue]Testing Target Monitoring...[/bold blue]")
        try:
            all_tweets = await self.target.monitor_targets()
            for target, tweets in all_tweets.items():
                console.print(f"[green]✓ Found {len(tweets)} tweets from @{target}[/green]")
                for tweet in tweets[:2]:  # Show first 2 tweets per target
                    console.print(Panel(
                        f"Time: {tweet['created_at']}\n"
                        f"Text: {tweet['text']}",
                        title=f"@{target}"
                    ))
        except Exception as e:
            console.print(f"[red]Error in target monitoring: {str(e)}[/red]")

    async def test_sentiment_analysis(self):
        """Test sentiment analysis"""
        console.print("\n[bold blue]Testing Sentiment Analysis...[/bold blue]")
        try:
            trending = await self.sentiment.scan_for_new_tokens()
            if trending:
                for token, data in trending.items():
                    console.print(Panel(
                        f"Trend Score: {data['trend_score']:.2f}\n"
                        f"Risk Score: {data['risk_score']:.2f}\n"
                        f"Mentions: {data['mention_count']}\n"
                        f"Unique Users: {data['unique_users']}\n"
                        f"First Seen: {data['first_seen'].strftime('%H:%M:%S')}\n"
                        f"Risk Flags: {', '.join(data.get('risk_flags', []))}\n"
                        f"Suspicious Claims: {', '.join(data.get('suspicious_claims', []))}",
                        title=f"Token: {token}",
                        style="green" if data['risk_score'] < 0.5 else "yellow"
                    ))
            else:
                console.print("[yellow]No trending tokens found[/yellow]")
        except Exception as e:
            console.print(f"[red]Error in sentiment analysis: {str(e)}[/red]")

    async def test_price_checking(self):
        """Test Solana price checking"""
        console.print("\n[bold blue]Testing Price Checking...[/bold blue]")
        try:
            # Test SOL price
            sol_address = "So11111111111111111111111111111111111111112"
            price = await self.solana.get_token_price(sol_address)
            if price:
                console.print(f"[green]✓ SOL price: ${price}[/green]")
            else:
                console.print("[red]✗ Failed to get SOL price[/red]")
            
            # Test recent token from tweets
            tweets = await self.twitter.get_relevant_tweets()
            for tweet in tweets:
                # Extract token address using Ollama
                analysis = await self.ollama.analyze_tweet(tweet['text'])
                if analysis.token_address:
                    price = await self.solana.get_token_price(analysis.token_address)
                    if price:
                        console.print(f"[green]✓ {analysis.token_symbols[0]} price: ${price}[/green]")
                    break
        except Exception as e:
            console.print(f"[red]Error in price checking: {str(e)}[/red]")

    async def test_tweet_analysis(self):
        """Test tweet analysis with Ollama"""
        console.print("\n[bold blue]Testing Tweet Analysis...[/bold blue]")
        try:
            # Get some recent tweets
            tweets = await self.twitter.get_relevant_tweets()
            for tweet in tweets[:3]:  # Analyze first 3 tweets
                analysis = await self.ollama.analyze_tweet(tweet['text'])
                console.print(Panel(
                    f"Tweet: {tweet['text']}\n\n"
                    f"Should Trade: {analysis.should_trade}\n"
                    f"Action: {analysis.action}\n"
                    f"Confidence: {analysis.confidence:.2f}\n"
                    f"Token: {analysis.token_symbols}\n"
                    f"Risk Level: {analysis.risk_level}\n"
                    f"Reasoning: {analysis.reasoning}",
                    title="Analysis Result",
                    style="green" if analysis.should_trade else "yellow"
                ))
        except Exception as e:
            console.print(f"[red]Error in tweet analysis: {str(e)}[/red]")

    async def run_all_tests(self):
        """Run all component tests"""
        console.print("[bold]Starting All Component Tests[/bold]")
        
        tests = [
            ("Twitter Scraping", self.test_twitter_scraping),
            ("Target Monitoring", self.test_target_monitoring),
            ("Sentiment Analysis", self.test_sentiment_analysis),
            ("Price Checking", self.test_price_checking),
            ("Tweet Analysis", self.test_tweet_analysis)
        ]
        
        results = Table(title="Test Results")
        results.add_column("Component", style="cyan")
        results.add_column("Status", style="green")
        
        for name, test in tests:
            try:
                console.print(f"\n[bold]Testing {name}...[/bold]")
                await test()
                results.add_row(name, "✓ Passed")
            except Exception as e:
                console.print(f"[red]Error in {name}: {str(e)}[/red]")
                results.add_row(name, "✗ Failed")
        
        console.print("\n")
        console.print(results)

async def main():
    load_dotenv()
    tester = ComponentTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main()) 