import snscrape.modules.twitter as sntwitter
from datetime import datetime, timedelta
import re
from collections import defaultdict
import asyncio

class TwitterScanner:
    def __init__(self):
        # Track token mentions with time decay
        self.token_mentions = defaultdict(lambda: {
            'first_seen': None,
            'mentions': [],  # List of (timestamp, engagement) tuples
            'unique_users': set(),
            'total_engagement': 0
        })
        
        print("Twitter scanner initialized")

    async def search_trending_tokens(self):
        """Get trending tokens using snscrape"""
        print("\nScanning for trending tokens...")
        
        try:
            # Search queries focused on crypto tokens
            search_queries = [
                "$ min_faves:50",  # Any $ with engagement
                "$SOL OR $BONK OR $WIF",  # Known tokens
                "solana $",  # Solana ecosystem
                "launch $",  # New launches
                "airdrop $"  # Airdrops
            ]
            
            current_time = datetime.now()
            cutoff_time = current_time - timedelta(hours=24)
            
            # Reset old data
            for data in self.token_mentions.values():
                # Remove mentions older than 24h
                data['mentions'] = [(t,e) for t,e in data['mentions'] if t > cutoff_time]
                data['total_engagement'] = sum(e for _,e in data['mentions'])
            
            for query in search_queries:
                try:
                    # Get recent tweets
                    tweets = sntwitter.TwitterSearchScraper(query).get_items()
                    
                    for i, tweet in enumerate(tweets):
                        if i > 100:  # Limit tweets per query
                            break
                            
                        if tweet.date < cutoff_time:
                            continue
                            
                        # Find $ tokens
                        tokens = re.findall(r'\$([A-Za-z0-9]{2,10})', tweet.rawContent.upper())
                        
                        if tokens:
                            # Calculate engagement
                            engagement = (
                                tweet.likeCount * 1.0 +
                                tweet.retweetCount * 2.0 +
                                tweet.replyCount * 0.5
                            )
                            
                            # Update token data
                            for token in tokens:
                                data = self.token_mentions[token]
                                
                                if not data['first_seen']:
                                    data['first_seen'] = tweet.date
                                    
                                data['mentions'].append((tweet.date, engagement))
                                data['unique_users'].add(tweet.user.username)
                                data['total_engagement'] += engagement
                                
                                print(f"Found ${token} with {engagement} engagement")
                                
                except Exception as e:
                    print(f"Error with search term {term}: {e}")
                    continue
                    
                await asyncio.sleep(1)
            
            # Calculate trending scores
            trending = []
            for token, data in self.token_mentions.items():
                if len(data['mentions']) == 0:
                    continue
                    
                # Calculate velocity (mentions in last hour)
                hour_ago = current_time - timedelta(hours=1)
                recent_mentions = len([t for t,_ in data['mentions'] if t > hour_ago])
                velocity = recent_mentions / 1.0  # Per hour
                
                # Calculate weighted engagement score
                engagement_score = 0
                for timestamp, engagement in data['mentions']:
                    # More recent engagements count more
                    time_diff = (current_time - timestamp).total_seconds() / 3600  # Hours
                    weight = 2 ** (-time_diff/12)  # Half-life of 12 hours
                    engagement_score += engagement * weight
                
                # Final trending score
                trend_score = (
                    velocity * 50 +  # Recent activity
                    len(data['unique_users']) * 30 +  # Unique users
                    engagement_score * 20  # Weighted engagement
                )
                
                trending.append({
                    'token': token,
                    'trend_score': trend_score,
                    'mentions': len(data['mentions']),
                    'engagement': data['total_engagement'],
                    'velocity': velocity
                })
            
            # Sort and get top 20
            trending.sort(key=lambda x: x['trend_score'], reverse=True)
            trending = trending[:20]
            
            print(f"Found {len(trending)} trending tokens")
            return trending

        except Exception as e:
            print(f"Error searching tweets: {e}")
            return []