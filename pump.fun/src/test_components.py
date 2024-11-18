import asyncio
import os
import argparse
from dotenv import load_dotenv
from rich.console import Console
from social.twitter_scanner import TwitterScanner
from ai.ollama_client import OllamaClient
from blockchain.solana_client import SolanaClient

console = Console()

async def test_twitter():
    console.print("\n[bold blue]Testing Twitter Scanner...[/bold blue]")
    scanner = TwitterScanner()
    
    console.print("Fetching tweets from @0xEcca...")
    try:
        tweets = await scanner.get_relevant_tweets()
        
        if tweets:
            console.print(f"[green]✓ Found {len(tweets)} tweets[/green]")
            for tweet in tweets:
                console.print(f"\nTime: {tweet['created_at']}")
                console.print(f"Text: {tweet['text']}")
        else:
            console.print("[yellow]! No tweets found. Trying web scraping fallback...[/yellow]")
            tweets = await scanner._scrape_tweets()
            if tweets:
                console.print(f"[green]✓ Found {len(tweets)} tweets via scraping[/green]")
                for tweet in tweets:
                    console.print(f"\nTime: {tweet['created_at']}")
                    console.print(f"Text: {tweet['text']}")
            else:
                console.print("[red]✗ No tweets found via any method[/red]")
    except Exception as e:
        console.print(f"[red]✗ Error testing Twitter: {str(e)}[/red]")
        import traceback
        traceback.print_exc()

async def test_ollama():
    console.print("\n[bold blue]Testing Ollama...[/bold blue]")
    try:
        client = OllamaClient(model="dolphin-mistral")
        
        # Updated test tweet with current market context
        test_tweet = "Just bought $SOL at $234, expecting pump to $300 soon! Strong momentum 🚀"
        
        console.print("Analyzing test tweet...")
        analysis = await client.analyze_tweet(test_tweet)
        
        if analysis:
            console.print("[green]✓ Analysis completed[/green]")
            console.print(f"Should trade: {analysis.should_trade}")
            console.print(f"Action: {analysis.action}")
            console.print(f"Confidence: {analysis.confidence}")
            console.print(f"Token: {analysis.token_symbols}")
            console.print(f"Entry Price: ${analysis.entry_price}")
            console.print(f"Target Price: ${analysis.target_price}")
            console.print(f"Reasoning: {analysis.reasoning}")
        else:
            console.print("[red]✗ Analysis failed[/red]")
    except Exception as e:
        console.print(f"[red]✗ Error testing Ollama: {str(e)}[/red]")
        import traceback
        traceback.print_exc()

async def test_solana():
    console.print("\n[bold blue]Testing Solana Client...[/bold blue]")
    try:
        client = SolanaClient()
        
        # Test SOL price fetch
        sol_address = "So11111111111111111111111111111111111111112"
        console.print("Fetching SOL price...")
        price = await client.get_token_price(sol_address)
        
        if price:
            console.print(f"[green]✓ SOL price: ${price}[/green]")
        else:
            console.print("[red]✗ Failed to get SOL price[/red]")
    except Exception as e:
        console.print(f"[red]✗ Error testing Solana: {str(e)}[/red]")
        import traceback
        traceback.print_exc()

async def main():
    load_dotenv()
    
    parser = argparse.ArgumentParser(description='Test trading bot components')
    parser.add_argument('--twitter-only', action='store_true', help='Test only Twitter')
    parser.add_argument('--ollama-only', action='store_true', help='Test only Ollama')
    parser.add_argument('--solana-only', action='store_true', help='Test only Solana')
    
    args = parser.parse_args()
    
    console.print("[bold]Starting Component Tests[/bold]")
    
    try:
        if args.twitter_only:
            await test_twitter()
        elif args.ollama_only:
            await test_ollama()
        elif args.solana_only:
            await test_solana()
        else:
            # Test all components
            await test_twitter()
            await test_ollama()
            await test_solana()
            
    except Exception as e:
        console.print(f"[red]Error during testing: {str(e)}[/red]")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 