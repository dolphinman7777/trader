import logging
from datetime import datetime
import os

class TradingLogger:
    def __init__(self):
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
        
        # Set up file handler
        log_file = f"logs/trading_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # Set up console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Set up logger
        self.logger = logging.getLogger('TradingBot')
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def log_tweet(self, tweet):
        self.logger.info(f"New tweet found: {tweet['text'][:100]}...")
    
    def log_analysis(self, analysis):
        self.logger.info(
            f"Analysis result: Should trade: {analysis.should_trade}, "
            f"Token: {analysis.token_symbols}, "
            f"Confidence: {analysis.confidence}, "
            f"Reasoning: {analysis.reasoning}"
        )
    
    def log_trade(self, token, action, amount, price):
        self.logger.info(
            f"Trade executed: {action.upper()} {amount} SOL worth of {token} "
            f"at price {price}"
        )
    
    def log_error(self, error):
        self.logger.error(f"Error occurred: {str(error)}") 