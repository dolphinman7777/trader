import asyncio
from rich.live import Live
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from social.twitter_scanner import TwitterScanner
from ai.ollama_client import OllamaClient
from blockchain.solana_client import SolanaClient
from datetime import datetime
import time
from social.target_scanner import TargetScanner
from social.sentiment_scanner import SentimentScanner

console = Console()

class TweetMonitor:
    def __init__(self):
        self.target_scanner = TargetScanner()
        self.sentiment_scanner = SentimentScanner()
        self.ollama = OllamaClient(model="dolphin-mistral")
        self.solana = SolanaClient()
        
    async def monitor(self):
        while True:
            try:
                # Monitor target accounts
                target_tweets = await self.target_scanner.monitor_targets()
                for target, tweets in target_tweets.items():
                    for tweet in tweets:
                        analysis = await self.ollama.analyze_tweet(tweet['text'])
                        if analysis.should_trade:
                            # Handle trading signals...
                            pass
                
                # Monitor new tokens
                trending_tokens = await self.sentiment_scanner.scan_for_new_tokens()
                for token, data in trending_tokens.items():
                    if data['trend_score'] > 2.0:  # High trend score
                        console.print(Panel(
                            f"New Token Alert!\n"
                            f"Symbol: {token}\n"
                            f"Trend Score: {data['trend_score']:.2f}\n"
                            f"Mentions: {data['mention_count']}\n"
                            f"Sentiment: {data['sentiment_score']:.2f}\n"
                            f"First Seen: {data['first_seen'].strftime('%H:%M:%S')}\n"
                            f"Unique Users: {data['unique_users']}",
                            title="New Token",
                            style="bold yellow"
                        ))
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                console.print(f"[red]Error: {str(e)}[/red]")
                await asyncio.sleep(60)

async def main():
    monitor = TweetMonitor()
    await monitor.monitor()

if __name__ == "__main__":
    asyncio.run(main()) 