import asyncio
import os
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from dotenv import load_dotenv

# Add parent directory to path
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trading.pump_trader import PumpTrader
from blockchain.solana_client import SolanaClient
from social.twitter_scanner import TwitterScanner
from ai.ollama_client import OllamaClient
from database.db_manager import DatabaseManager
from utils.logger import TradingLogger
from cli.trading_cli import TradingCLI

console = Console()

def check_environment():
    """Check if all required environment variables are set"""
    required_vars = [
        'TWITTER_BEARER_TOKEN',
        'TWITTER_API_KEY',
        'TWITTER_API_SECRET',
        'TWITTER_ACCESS_TOKEN',
        'TWITTER_ACCESS_TOKEN_SECRET',
        'SOLANA_PRIVATE_KEY',
        'SOLANA_RPC_ENDPOINT'
    ]
    
    missing = [var for var in required_vars if not os.getenv(var)]
    return missing

def check_ollama():
    """Check if Ollama is running"""
    import requests
    try:
        response = requests.get("http://localhost:11434/api/tags")
        return response.status_code == 200
    except:
        return False

async def trading_bot(logger, db, ollama_client, twitter_scanner, solana_client, trader):
    """Trading bot logic"""
    logger.logger.info("Trading bot started")
    
    while True:
        try:
            tweets = await twitter_scanner.get_relevant_tweets()
            
            for tweet in tweets:
                logger.log_tweet(tweet)
                analysis = await ollama_client.analyze_tweet(tweet['text'])
                logger.log_analysis(analysis)
                
                if analysis.should_trade:
                    success = await trader.execute_trade(
                        token_address=analysis.token_address,
                        action=analysis.action,
                        amount=analysis.suggested_amount,
                        tweet_id=str(tweet['id']),
                        confidence=analysis.confidence,
                        token_symbol=analysis.token_symbols[0] if analysis.token_symbols else "UNKNOWN"
                    )
                    
                    if success:
                        logger.log_trade(
                            analysis.token_symbols[0],
                            analysis.action,
                            analysis.suggested_amount,
                            await solana_client.get_token_price(analysis.token_address)
                        )
            
            await db.update_performance_metrics()
            await asyncio.sleep(10)
            
        except Exception as e:
            logger.log_error(e)
            await asyncio.sleep(30)

async def main():
    """Main execution function"""
    load_dotenv()
    
    # Environment checks
    console.print(Panel("🔍 Performing system checks...", style="blue"))
    
    # Check environment variables
    missing_vars = check_environment()
    if missing_vars:
        console.print(Panel(
            f"❌ Missing environment variables: {', '.join(missing_vars)}", 
            style="red"
        ))
        return
    
    # Check Ollama
    if not check_ollama():
        console.print(Panel(
            "❌ Ollama is not running. Please start Ollama first:\n" +
            "   Run: ollama serve", 
            style="red"
        ))
        return
    
    # Initialize components
    logger = TradingLogger()
    db = DatabaseManager()
    ollama_client = OllamaClient(model="dolphin-mistral")
    twitter_scanner = TwitterScanner()
    solana_client = SolanaClient()
    trader = PumpTrader(solana_client)
    trading_cli = TradingCLI()

    # Display configuration
    config_table = Table(title="Bot Configuration")
    config_table.add_column("Setting", style="cyan")
    config_table.add_column("Value", style="green")
    config_table.add_row("RPC Endpoint", os.getenv('SOLANA_RPC_ENDPOINT'))
    config_table.add_row("Max Trade Amount", f"{os.getenv('MAX_TRADE_AMOUNT')} SOL")
    config_table.add_row("Stop Loss", f"{float(os.getenv('STOP_LOSS_PERCENTAGE'))*100}%")
    config_table.add_row("Take Profit", f"{float(os.getenv('TAKE_PROFIT_PERCENTAGE'))*100}%")
    console.print(config_table)
    
    console.print(Panel("🚀 Starting trading bot...", style="green"))
    
    try:
        # Start both the trading bot and CLI
        await asyncio.gather(
            trading_cli.run(),
            trading_bot(
                logger, db, ollama_client, 
                twitter_scanner, solana_client, trader
            )
        )
    except KeyboardInterrupt:
        console.print(Panel("👋 Bot stopped by user", style="yellow"))
    except Exception as e:
        console.print(Panel(f"❌ Error: {str(e)}", style="red"))

if __name__ == "__main__":
    asyncio.run(main()) 