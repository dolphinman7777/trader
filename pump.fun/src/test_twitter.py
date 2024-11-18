import tweepy
import os
from dotenv import load_dotenv

def test_twitter_connection():
    load_dotenv()
    
    # Print credentials (partially masked)
    print("\nChecking Twitter credentials:")
    print(f"Bearer Token: {os.getenv('TWITTER_BEARER_TOKEN')[:10]}...")
    print(f"API Key: {os.getenv('TWITTER_API_KEY')[:10]}...")
    
    # Initialize Twitter client
    client = tweepy.Client(
        bearer_token=os.getenv('TWITTER_BEARER_TOKEN'),
        consumer_key=os.getenv('TWITTER_API_KEY'),
        consumer_secret=os.getenv('TWITTER_API_SECRET'),
        access_token=os.getenv('TWITTER_ACCESS_TOKEN'),
        access_token_secret=os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
    )
    
    try:
        # Try to get user info
        print("\nTrying to get user info for @0xEcca...")
        user = client.get_user(username="0xEcca")
        if user.data:
            print(f"Found user: ID={user.data.id}")
            
            # Try to get recent tweets
            print("\nTrying to get recent tweets...")
            tweets = client.get_users_tweets(
                id=user.data.id,
                max_results=10,
                tweet_fields=['created_at', 'text']
            )
            
            if tweets.data:
                print(f"\nFound {len(tweets.data)} tweets:")
                for tweet in tweets.data:
                    print(f"\nTime: {tweet.created_at}")
                    print(f"Text: {tweet.text[:100]}...")
            else:
                print("No tweets found")
        else:
            print("User not found")
            
    except Exception as e:
        print(f"\nError: {str(e)}")
        print("Full error details:", e)

if __name__ == "__main__":
    test_twitter_connection() 