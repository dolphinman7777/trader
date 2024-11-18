import asyncio
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt
from dotenv import load_dotenv

from social.twitter_scanner import TwitterScanner
from ai.ollama_client import OllamaClient
from blockchain.solana_client import SolanaClient

console = Console()

async def test_tweet_analysis(tweet_text: str):
    """Test AI analysis on a specific tweet"""
    console.print(Panel(f"Analyzing tweet:\n{tweet_text}", title="Input"))
    
    client = OllamaClient(model="dolphin-mistral")
    analysis = await client.analyze_tweet(tweet_text)
    
    # Display results in a table
    table = Table(title="Analysis Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Should Trade", str(analysis.should_trade))
    table.add_row("Action", str(analysis.action))
    table.add_row("Confidence", f"{analysis.confidence:.2f}")
    table.add_row("Token", str(analysis.token_symbols))
    table.add_row("Token Address", str(analysis.token_address))
    table.add_row("Risk Level", analysis.risk_level)
    if analysis.multiplier:
        table.add_row("Multiplier", f"x{analysis.multiplier}")
    if analysis.entry_price:
        table.add_row("Entry Price", f"${analysis.entry_price}")
    if analysis.target_price:
        table.add_row("Target Price", f"${analysis.target_price}")
    table.add_row("Reasoning", analysis.reasoning)
    
    console.print(table)

async def test_price_check(token_address: str):
    """Test price fetching for a token"""
    client = SolanaClient()
    price = await client.get_token_price(token_address)
    
    if price:
        console.print(f"[green]Price for {token_address}: ${price}[/green]")
    else:
        console.print(f"[red]Could not get price for {token_address}[/red]")

async def monitor_tweets():
    """Monitor live tweets from @ecca"""
    scanner = TwitterScanner()
    ollama = OllamaClient(model="dolphin-mistral")
    
    console.print("[yellow]Monitoring @ecca's tweets... Press Ctrl+C to stop[/yellow]")
    
    try:
        while True:
            tweets = await scanner.get_relevant_tweets()
            for tweet in tweets:
                console.print(Panel(
                    f"Time: {tweet['created_at']}\n"
                    f"Text: {tweet['text']}\n"
                    f"Metrics: {tweet['metrics']}",
                    title="New Tweet"
                ))
                
                # Analyze tweet
                analysis = await ollama.analyze_tweet(tweet['text'])
                if analysis.should_trade:
                    console.print(Panel(
                        f"Trading Signal Detected!\n"
                        f"Action: {analysis.action}\n"
                        f"Token: {analysis.token_symbols}\n"
                        f"Confidence: {analysis.confidence:.2f}\n"
                        f"Reasoning: {analysis.reasoning}",
                        title="Trading Signal",
                        style="green"
                    ))
            
            await asyncio.sleep(10)
    except KeyboardInterrupt:
        console.print("[yellow]Monitoring stopped[/yellow]")

@click.group()
def cli():
    """Trading Bot Test CLI"""
    pass

@cli.command()
def monitor():
    """Monitor @ecca's tweets in real-time"""
    asyncio.run(monitor_tweets())

@cli.command()
@click.argument('token_address')
def price(token_address):
    """Check price for a token address"""
    asyncio.run(test_price_check(token_address))

@cli.command()
def analyze():
    """Analyze a specific tweet"""
    tweet = Prompt.ask("Enter tweet text")
    asyncio.run(test_tweet_analysis(tweet))

@cli.command()
def interactive():
    """Interactive testing mode"""
    while True:
        console.print("\n[bold cyan]Available commands:[/bold cyan]")
        console.print("1. Monitor tweets")
        console.print("2. Check token price")
        console.print("3. Analyze tweet")
        console.print("4. Exit")
        
        choice = Prompt.ask("Select option", choices=["1", "2", "3", "4"])
        
        if choice == "1":
            asyncio.run(monitor_tweets())
        elif choice == "2":
            token = Prompt.ask("Enter token address")
            asyncio.run(test_price_check(token))
        elif choice == "3":
            tweet = Prompt.ask("Enter tweet text")
            asyncio.run(test_tweet_analysis(tweet))
        else:
            break

if __name__ == "__main__":
    load_dotenv()
    cli() 