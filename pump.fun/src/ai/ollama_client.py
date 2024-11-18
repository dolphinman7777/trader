import requests
import json
from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple
import re
from datetime import datetime

@dataclass
class TradeAnalysis:
    should_trade: bool
    token_address: Optional[str] = None
    action: Optional[str] = None  # 'buy' or 'sell'
    suggested_amount: float = 0.0
    confidence: float = 0.0
    reasoning: str = ""
    token_symbols: List[str] = None
    risk_level: str = "high"
    multiplier: Optional[float] = None
    target_price: Optional[float] = None
    entry_price: Optional[float] = None

class OllamaClient:
    def __init__(self, model: str, host: str = "http://localhost:11434"):
        self.model = model
        self.host = host
        self.api_endpoint = f"{host}/api/generate"
        
        # Known token addresses
        self.token_addresses = {
            'sol': 'So11111111111111111111111111111111111111112',
            'ray': '4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R',
            'orca': 'orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE',
            'bonk': 'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263',
        }

    async def analyze_tweet(self, tweet_text: str) -> TradeAnalysis:
        try:
            prompt = f"""
            Analyze this cryptocurrency trading tweet and respond in JSON format:
            "{tweet_text}"

            Response format:
            {{
                "should_trade": true/false,
                "token_symbols": ["list", "of", "tokens"],
                "action": "buy"/"sell"/null,
                "confidence": 0.0-1.0,
                "risk_level": "high"/"medium"/"low",
                "reasoning": "brief explanation",
                "suggested_amount": 0.0-1.0
            }}

            Consider:
            1. Is there a clear trading signal?
            2. Are specific tokens mentioned?
            3. Is there price/target information?
            4. What's the risk level?
            5. How much confidence in the signal?

            Be conservative with confidence scores.
            """

            response = requests.post(
                self.api_endpoint,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.3
                }
            )

            if response.status_code == 200:
                # Extract JSON from response
                response_text = response.json()['response']
                json_match = re.search(r'\{[\s\S]*\}', response_text)
                if not json_match:
                    return TradeAnalysis(should_trade=False, reasoning="Could not parse response")
                
                analysis_dict = json.loads(json_match.group())
                
                # Extract token symbols and find addresses
                token_symbols = analysis_dict.get('token_symbols', [])
                token_address = None
                for symbol in token_symbols:
                    symbol = symbol.lower()
                    if symbol in self.token_addresses:
                        token_address = self.token_addresses[symbol]
                        break

                return TradeAnalysis(
                    should_trade=analysis_dict.get('should_trade', False),
                    token_address=token_address,
                    action=analysis_dict.get('action'),
                    suggested_amount=float(analysis_dict.get('suggested_amount', 0.0)),
                    confidence=float(analysis_dict.get('confidence', 0.0)),
                    reasoning=analysis_dict.get('reasoning', ''),
                    token_symbols=token_symbols,
                    risk_level=analysis_dict.get('risk_level', 'high')
                )
            else:
                print(f"Error from Ollama API: {response.status_code}")
                return TradeAnalysis(should_trade=False)

        except Exception as e:
            print(f"Error in analyze_tweet: {e}")
            return TradeAnalysis(should_trade=False)