import asyncio
from rich.console import Console
from rich.table import Table
from dotenv import load_dotenv
from social.twitter_scanner import TwitterScanner
import time

console = Console()

async def test_scraping():
    scanner = TwitterScanner()
    
    console.print("[yellow]Starting Twitter scraping test...[/yellow]")
    
    try:
        # Try to get tweets
        console.print("Fetching @ecca's tweets...")
        tweets = await scanner.get_relevant_tweets()
        
        if tweets:
            # Display tweets in a table
            table = Table(title="Latest Tweets from @ecca")
            table.add_column("Time", style="cyan")
            table.add_column("Text", style="white")
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
                    tweet['text'][:100] + ("..." if len(tweet['text']) > 100 else ""),
                    metrics_str
                )
            
            console.print(table)
            console.print(f"[green]✓ Successfully fetched {len(tweets)} tweets[/green]")
            
            # Print detailed info for debugging
            console.print("\n[bold]Detailed Tweet Info:[/bold]")
            for tweet in tweets:
                console.print(f"\n[cyan]Tweet ID:[/cyan] {tweet.get('id')}")
                console.print(f"[cyan]Time:[/cyan] {tweet['created_at']}")
                console.print(f"[cyan]Text:[/cyan] {tweet['text']}")
                console.print(f"[cyan]Metrics:[/cyan] {tweet['metrics']}")
                console.print(f"[cyan]Source:[/cyan] {tweet.get('source', 'unknown')}")
                console.print("---")
                
        else:
            console.print("[red]No tweets found[/red]")
            
    except Exception as e:
        console.print(f"[red]Error during testing: {str(e)}[/red]")
        import traceback
        traceback.print_exc()

async def main():
    load_dotenv()
    await test_scraping()

if __name__ == "__main__":
    asyncio.run(main()) 