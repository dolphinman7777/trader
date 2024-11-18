from typing import List, Dict, Set
import re
from collections import defaultdict
from datetime import datetime, timedelta
import networkx as nx
from textblob import TextBlob
import emoji
from .twitter_scanner import TwitterScanner
import math

class SentimentScanner:
    def __init__(self):
        self.scanner = TwitterScanner()
        # Enhanced keywords with categories
        self.token_patterns = {
            'launch_keywords': [
                "launch", "presale", "stealth launch", "fair launch",
                "just launched", "launching", "airdrop", "mint"
            ],
            'hype_keywords': [
                "gem", "moonshot", "100x", "1000x", "moon", "pump",
                "bullish", "LFG", "don't miss", "early"
            ],
            'caution_keywords': [
                "scam", "rug", "honeypot", "fake", "beware",
                "copy", "clone", "sus", "suspicious"
            ]
        }
        
        # Token detection patterns
        self.token_detection = {
            'symbol': r'\$([A-Z0-9]{2,10})',  # Standard $TOKEN format
            'address': r'([A-Za-z0-9]{32,44})(pump)?',  # Solana address
            'pair': r'([A-Z0-9]{2,10})[-/]SOL',  # Trading pair format
            'domain': r'([A-Z0-9]{2,10})\.pump',  # .pump domain format
            'handle': r'@([A-Z0-9]{2,10})_pump'   # Twitter handle format
        }
        
        # Network analysis
        self.interaction_graph = nx.DiGraph()
        self.influencer_scores = defaultdict(float)
        
        # Token tracking with enhanced metrics
        self.token_mentions = defaultdict(lambda: {
            'first_seen': None,
            'last_seen': None,
            'mention_count': 0,
            'unique_users': set(),
            'sentiment_scores': [],
            'price_mentions': [],
            'addresses': set(),
            'influencer_mentions': set(),  # Track who mentioned it
            'related_tokens': set(),  # Tokens mentioned together
            'launch_signals': 0,
            'hype_signals': 0,
            'caution_signals': 0,
            'volume_history': [],  # Track mention volume over time
            'sentiment_history': []  # Track sentiment over time
        })
        
        # Enhanced token patterns
        self.token_patterns.update({
            'scam_patterns': [
                r'(\d+)% tax',  # High tax tokens
                r'(LP locked|liquidity locked) for (\d+)',  # Short LP locks
                r'max(\s+)?wallet (\d+)%',  # Restrictive max wallet
                r'max(\s+)?tx (\d+)%',  # Restrictive max tx
                r'renounced',  # Ownership claims
                r'honeypot',  # Explicit warnings
                r'contract verified',  # Contract claims
            ],
            'volume_patterns': [
                r'(\d+(?:\.\d+)?[kmb]?) (24h|daily) vol',  # Volume claims
                r'mcap[: ]?\$?(\d+(?:\.\d+)?[kmb]?)',  # Market cap claims
                r'(\d+(?:\.\d+)?[kmb]?) holders',  # Holder claims
            ],
            'pump_patterns': [
                r'(\d+)x(?: in)? (\d+)(m|min|minutes?|h|hours?)',  # Pump claims
                r'(\d+)% up',  # Percentage gains
                r'(bottomed|bottom|dip)',  # Bottom signals
                r'(reversal|reversed|reversing)',  # Reversal claims
            ],
            'influencer_patterns': [
                r'@([A-Za-z0-9_]+) (called|mentioned|talking)',  # Influencer mentions
                r'(followed by|tracking) @([A-Za-z0-9_]+)',  # Influencer tracking
                r'(big|huge|whale) (buyer|buying|accumulation)',  # Whale activity
            ]
        })

    def _calculate_advanced_sentiment(self, text: str) -> Dict:
        """Calculate detailed sentiment metrics"""
        # Basic sentiment using TextBlob
        blob = TextBlob(text)
        base_sentiment = blob.sentiment.polarity
        
        # Adjust for crypto-specific factors
        sentiment_adjustments = 0
        
        # Check for emojis
        emoji_sentiment = {
            '🚀': 0.3, '💎': 0.2, '🌙': 0.2, '📈': 0.2,  # Positive
            '🔥': 0.15, '💪': 0.1, '✨': 0.1,
            '⚠️': -0.2, '🚨': -0.1, '📉': -0.2  # Negative
        }
        for char in text:
            if char in emoji_sentiment:
                sentiment_adjustments += emoji_sentiment[char]
        
        # Check for price targets and multipliers
        price_matches = re.finditer(r'(\d+)x', text.lower())
        for match in price_matches:
            multiplier = int(match.group(1))
            if multiplier > 100:
                sentiment_adjustments += 0.3
            elif multiplier > 10:
                sentiment_adjustments += 0.2
        
        # Check for urgency signals
        urgency_words = ["now", "quick", "fast", "hurry", "soon", "don't miss"]
        urgency_count = sum(1 for word in urgency_words if word in text.lower())
        sentiment_adjustments += urgency_count * 0.1
        
        # Calculate final sentiment
        final_sentiment = min(max(base_sentiment + sentiment_adjustments, -1.0), 1.0)
        
        return {
            'sentiment': final_sentiment,
            'confidence': blob.sentiment.subjectivity,
            'urgency': urgency_count,
            'emoji_sentiment': sum(emoji_sentiment.get(c, 0) for c in text),
            'price_targets': bool(re.search(r'\$\d+', text))
        }

    def _extract_token_info(self, text: str) -> List[Dict]:
        """Extract detailed token information"""
        tokens = []
        
        # Check all token patterns
        for pattern_type, pattern in self.token_detection.items():
            matches = re.finditer(pattern, text)
            for match in matches:
                token_info = {
                    'symbol': match.group(1),
                    'type': pattern_type,
                    'full_match': match.group(0),
                    'position': match.span(),
                    'context': text[max(0, match.start()-20):min(len(text), match.end()+20)]
                }
                tokens.append(token_info)
        
        return tokens

    def _analyze_network(self, tweet: Dict, tokens: List[Dict]):
        """Analyze social network and token relationships"""
        author = tweet['author_id']
        
        # Update interaction graph
        if author not in self.interaction_graph:
            self.interaction_graph.add_node(author, mentions=0, influence_score=0)
        
        # Update influencer score based on engagement
        metrics = tweet.get('metrics', {})
        engagement = (
            metrics.get('like_count', 0) * 1 +
            metrics.get('retweet_count', 0) * 2 +
            metrics.get('reply_count', 0) * 1.5
        )
        self.influencer_scores[author] += engagement
        
        # Track token co-mentions
        mentioned_tokens = set(token['symbol'] for token in tokens)
        if len(mentioned_tokens) > 1:
            for token1 in mentioned_tokens:
                for token2 in mentioned_tokens:
                    if token1 != token2:
                        self.token_mentions[token1]['related_tokens'].add(token2)

    def _analyze_token_patterns(self, text: str, token_data: Dict):
        """Analyze detailed token patterns"""
        text_lower = text.lower()
        
        # Check scam patterns
        for pattern in self.token_patterns['scam_patterns']:
            if matches := re.finditer(pattern, text_lower):
                for match in matches:
                    if 'tax' in pattern and int(match.group(1)) > 10:
                        token_data['risk_flags'].append(f"High tax: {match.group(1)}%")
                    elif 'locked' in pattern and int(match.group(2)) < 30:
                        token_data['risk_flags'].append(f"Short lock: {match.group(2)} days")
                    elif 'max' in pattern and int(match.group(2)) < 1:
                        token_data['risk_flags'].append(f"Restrictive max: {match.group(2)}%")

        # Check volume patterns
        for pattern in self.token_patterns['volume_patterns']:
            if matches := re.finditer(pattern, text_lower):
                for match in matches:
                    value = self._parse_number(match.group(1))
                    if 'vol' in pattern:
                        token_data['volume_claims'].append(value)
                    elif 'mcap' in pattern:
                        token_data['mcap_claims'].append(value)
                    elif 'holders' in pattern:
                        token_data['holder_claims'].append(value)

        # Check pump patterns
        for pattern in self.token_patterns['pump_patterns']:
            if matches := re.finditer(pattern, text_lower):
                for match in matches:
                    if 'x' in pattern:
                        multiplier = int(match.group(1))
                        timeframe = match.group(2)
                        if multiplier > 10 and 'm' in timeframe:
                            token_data['suspicious_claims'].append(f"{multiplier}x in {timeframe}")
                    elif 'up' in pattern:
                        percentage = int(match.group(1))
                        if percentage > 100:
                            token_data['suspicious_claims'].append(f"{percentage}% up")

        # Track influencer mentions
        for pattern in self.token_patterns['influencer_patterns']:
            if matches := re.finditer(pattern, text_lower):
                for match in matches:
                    if 'whale' in pattern:
                        token_data['whale_activity'] += 1
                    else:
                        influencer = match.group(1) or match.group(2)
                        token_data['influencer_mentions'].add(influencer)

    def _calculate_risk_score(self, token_data: Dict) -> float:
        """Calculate sophisticated risk score"""
        risk_score = 0.0
        
        # Base risk from flags
        risk_score += len(token_data['risk_flags']) * 0.5
        risk_score += len(token_data['suspicious_claims']) * 0.3
        
        # Volume and market cap analysis
        if token_data['volume_claims']:
            avg_volume = sum(token_data['volume_claims']) / len(token_data['volume_claims'])
            if avg_volume < 10000:  # Less than $10k daily volume
                risk_score += 0.5
        else:
            risk_score += 0.3  # No volume data is suspicious
            
        # Holder analysis
        if token_data['holder_claims']:
            avg_holders = sum(token_data['holder_claims']) / len(token_data['holder_claims'])
            if avg_holders < 100:
                risk_score += 0.4
                
        # Time-based risk
        time_since_first = (datetime.now() - token_data['first_seen']).total_seconds() / 3600
        if time_since_first < 1:  # Less than 1 hour old
            risk_score += 0.6
        elif time_since_first < 24:  # Less than 24 hours old
            risk_score += 0.3
            
        # Mention velocity risk
        mention_velocity = token_data['mention_count'] / max(time_since_first, 1)
        if mention_velocity > 10:  # More than 10 mentions per hour
            risk_score += 0.4
            
        # Influencer risk
        unique_influencers = len(token_data['influencer_mentions'])
        if unique_influencers == 0:
            risk_score += 0.2
        elif unique_influencers > 5:  # Too many influencers too quickly is suspicious
            risk_score += 0.3
            
        # Normalize to 0-1 range
        return min(max(risk_score, 0.0), 1.0)

    def _calculate_trend_score(self, token_data: Dict) -> float:
        """Calculate trend score with enhanced metrics"""
        current_time = datetime.now()
        
        # Time decay factor (newer mentions worth more)
        time_diff = (current_time - token_data['first_seen']).total_seconds() / 3600
        recency_score = math.exp(-time_diff / 12)  # 12-hour half-life
        
        # Volume acceleration (rate of change in mention velocity)
        recent_mentions = [v for v in token_data['volume_history'] 
                         if (current_time - v['time']).total_seconds() < 3600]
        volume_acceleration = len(recent_mentions) / max(time_diff, 1)
        
        # Engagement quality score
        engagement_score = sum(v['engagement'] for v in token_data['volume_history'][-10:]) / 10
        
        # Influencer impact
        influencer_weight = sum(self.influencer_scores.get(inf, 0) 
                              for inf in token_data['influencer_mentions'])
        
        # Combine scores with weights
        base_score = (
            token_data['mention_count'] * 0.15 +
            len(token_data['unique_users']) * 0.15 +
            volume_acceleration * 0.2 +
            engagement_score * 0.2 +
            influencer_weight * 0.15 +
            recency_score * 0.15
        )
        
        return base_score * (1 - token_data.get('risk_score', 0) * 0.5)

    async def scan_for_new_tokens(self) -> Dict:
        """Enhanced token scanning with detailed metrics"""
        tweets = await self.scanner.search_tweets(
            [kw for cat in self.token_patterns.values() for kw in cat]
        )
        
        current_time = datetime.now()
        
        for tweet in tweets:
            # Extract and analyze tokens
            tokens = self._extract_token_info(tweet['text'])
            sentiment_data = self._calculate_advanced_sentiment(tweet['text'])
            
            # Analyze social network
            self._analyze_network(tweet, tokens)
            
            # Update token metrics
            for token in tokens:
                symbol = token['symbol']
                token_data = self.token_mentions[symbol]
                
                # Update basic metrics
                if not token_data['first_seen']:
                    token_data['first_seen'] = current_time
                token_data['last_seen'] = current_time
                token_data['mention_count'] += 1
                token_data['unique_users'].add(tweet['author_id'])
                
                # Update sentiment history
                token_data['sentiment_scores'].append(sentiment_data['sentiment'])
                token_data['sentiment_history'].append({
                    'time': current_time,
                    'sentiment': sentiment_data['sentiment'],
                    'confidence': sentiment_data['confidence']
                })
                
                # Track volume
                token_data['volume_history'].append({
                    'time': current_time,
                    'mentions': 1,
                    'engagement': sum(tweet.get('metrics', {}).values())
                })
                
                # Update signal counts
                text_lower = tweet['text'].lower()
                token_data['launch_signals'] += any(kw in text_lower for kw in self.token_patterns['launch_keywords'])
                token_data['hype_signals'] += any(kw in text_lower for kw in self.token_patterns['hype_keywords'])
                token_data['caution_signals'] += any(kw in text_lower for kw in self.token_patterns['caution_keywords'])
                
                # Track influencer mentions
                if self.influencer_scores[tweet['author_id']] > 1000:  # Threshold for influencer
                    token_data['influencer_mentions'].add(tweet['author_id'])
                
                # Analyze token patterns
                self._analyze_token_patterns(tweet['text'], token_data)
        
        return self._get_trending_tokens()

    def _get_trending_tokens(self) -> Dict:
        """Get trending tokens with enhanced scoring"""
        trending = {}
        current_time = datetime.now()
        
        for token, data in self.token_mentions.items():
            if (current_time - data['first_seen']) > timedelta(hours=24):
                continue
            
            # Calculate metrics
            avg_sentiment = sum(data['sentiment_scores']) / len(data['sentiment_scores']) if data['sentiment_scores'] else 0
            mention_velocity = len(data['volume_history']) / ((current_time - data['first_seen']).total_seconds() / 3600)
            
            # Calculate risk score
            risk_score = self._calculate_risk_score(data)
            
            # Calculate trend score with risk adjustment
            base_trend_score = (
                data['mention_count'] * 0.2 +
                len(data['unique_users']) * 0.2 +
                (avg_sentiment + 1) * 0.2 +
                mention_velocity * 0.2 +
                len(data['influencer_mentions']) * 0.2
            )
            
            # Adjust trend score based on risk
            adjusted_trend_score = base_trend_score * (1 - risk_score * 0.5)
            
            if adjusted_trend_score > 1.0:
                trending[token] = {
                    'trend_score': adjusted_trend_score,
                    'risk_score': risk_score,
                    'risk_flags': data['risk_flags'],
                    'suspicious_claims': data['suspicious_claims'],
                    'mention_count': data['mention_count'],
                    'unique_users': len(data['unique_users']),
                    'avg_sentiment': avg_sentiment,
                    'mention_velocity': mention_velocity,
                    'influencers': list(data['influencer_mentions']),
                    'whale_activity': data['whale_activity'],
                    'volume_data': data['volume_claims'],
                    'first_seen': data['first_seen'],
                    'addresses': list(data['addresses']),
                    'related_tokens': list(data['related_tokens'])
                }
        
        return trending 