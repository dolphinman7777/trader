import asyncio
from dotenv import load_dotenv
from ai.ollama_client import OllamaClient
from social.twitter_scanner import TwitterScanner
from blockchain.solana_client import SolanaClient
from trading.pump_trader import PumpTrader
from utils.logger import TradingLogger
from database.db_manager import DatabaseManager
from cli.trading_cli import TradingCLI
from datetime import datetime

load_dotenv()

async def trading_bot():
    # Initialize components
    logger = TradingLogger()
    db = DatabaseManager()
    ollama_client = OllamaClient(model="dolphin-mistral")
    twitter_scanner = TwitterScanner()
    solana_client = SolanaClient()
    trader = PumpTrader(solana_client)

    logger.logger.info("Trading bot started")

    while True:
        try:
            # Get latest tweets
            tweets = await twitter_scanner.get_relevant_tweets()
            
            for tweet in tweets:
                logger.log_tweet(tweet)
                
                # Analyze tweets with Ollama
                analysis = await ollama_client.analyze_tweet(tweet['text'])
                logger.log_analysis(analysis)
                
                if analysis.should_trade:
                    # Execute trade based on analysis
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
            
            # Update performance metrics every iteration
            await db.update_performance_metrics()
            
            # Log performance summary every hour
            if datetime.now().minute == 0:
                summary = await db.get_performance_summary()
                logger.logger.info(f"Performance Summary: {summary}")
            
            await asyncio.sleep(10)
            
        except Exception as e:
            logger.log_error(e)
            await asyncio.sleep(30)

async def main():
    # Start both the trading bot and CLI
    await asyncio.gather(
        trading_bot(),
        TradingCLI().run()
    )

if __name__ == "__main__":
    asyncio.run(main()) 