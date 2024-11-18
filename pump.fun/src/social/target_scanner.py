from typing import List, Dict
from datetime import datetime
import asyncio
from .twitter_scanner import TwitterScanner

class TargetScanner:
    def __init__(self):
        self.scanner = TwitterScanner()
        # List of high-value targets to monitor
        self.targets = [
            "ecca",
            "0xRamonos",
            "0xSolape",
            "SOLBigBrain",
            # Add more targets here
        ]
        self.cache = {}

    async def monitor_targets(self) -> Dict[str, List[Dict]]:
        """Monitor all target accounts"""
        all_tweets = {}
        
        for target in self.targets:
            try:
                self.scanner.primary_account = target
                tweets = await self.scanner.get_relevant_tweets()
                if tweets:
                    all_tweets[target] = tweets
            except Exception as e:
                print(f"Error monitoring {target}: {e}")
                continue
                
        return all_tweets 