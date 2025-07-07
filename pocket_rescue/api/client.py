#!/usr/bin/env python3
"""
Pocket API client for retrieving articles.
Handles paginated retrieval with rate limiting.
"""

import requests
import time
import json
from .auth import PocketAuth

# Pocket API endpoint for retrieving articles
RETRIEVE_URL = "https://getpocket.com/v3/get"


class PocketClient:
    def __init__(self, consumer_key=None):
        """Initialize Pocket API client."""
        self.auth = PocketAuth(consumer_key)
        self.access_token = None
        
    def authenticate(self, force_reauth=False):
        """Authenticate with Pocket API."""
        self.access_token = self.auth.authenticate(force_reauth)
        return self.access_token
        
    def retrieve_articles(self, count=30, detail_type="complete", state="all", sort="newest"):
        """
        Retrieve all articles from Pocket using pagination.
        
        Args:
            count: Number of articles per request (max 30)
            detail_type: Level of detail (simple, complete)
            state: Article state (unread, archive, all)
            sort: Sort order (newest, oldest, title, site)
            
        Returns:
            Dict with all articles in format: {"list": {article_id: article_data, ...}}
        """
        if not self.access_token:
            raise Exception("Not authenticated. Call authenticate() first.")
            
        all_articles = []
        offset = 0
        total_requests = 0
        
        print(f"Retrieving articles from Pocket API...")
        print(f"Parameters: count={count}, state={state}, sort={sort}")
        print("=" * 50)
        
        # Validate state parameter
        valid_states = ['unread', 'archive', 'all']
        if state not in valid_states:
            raise ValueError(f"Invalid state '{state}'. Must be one of: {valid_states}")

        while True:
            data = {
                "consumer_key": self.auth.consumer_key,
                "access_token": self.access_token,
                "count": count,
                "detailType": detail_type,
                "state": state,
                "sort": sort,
                "offset": offset
            }

            # Debug: show API request details for first request
            if total_requests == 0:
                print(f"🔍 API Request Details:")
                print(f"   URL: {RETRIEVE_URL}")
                print(f"   State: {state}")
                print(f"   Count: {count}")
                print(f"   Offset: {offset}")
                print()

            try:
                response = requests.post(RETRIEVE_URL, data=data, verify=True)
                total_requests += 1
                
                if response.status_code == 200:
                    result = response.json()
                    articles = result.get('list', {})

                    # Debug: show API response details for first request
                    if total_requests == 1:
                        print(f"📥 API Response Summary:")
                        print(f"   Status: {result.get('status', 'unknown')}")
                        print(f"   Complete: {result.get('complete', 'unknown')}")
                        print(f"   List type: {type(articles)}")
                        print(f"   Articles found: {len(articles) if articles else 0}")
                        if hasattr(result, 'keys'):
                            print(f"   Response keys: {list(result.keys())}")
                        print()

                    if not articles:  # No more articles to retrieve
                        if total_requests == 1:
                            print(f"⚠️  No articles found on first request - this might indicate:")
                            print(f"   • No articles in '{state}' state")
                            print(f"   • API parameter issue")
                            print(f"   • Account has no articles of this type")
                        print(f"\n✓ No more articles found")
                        break

                    # Convert to list for easier handling
                    article_list = list(articles.values())
                    all_articles.extend(article_list)

                    print(f"Batch {total_requests}: Retrieved {len(article_list)} articles (total: {len(all_articles)})", flush=True)

                    # Check if we got fewer articles than requested (last page)
                    if len(article_list) < count:
                        print(f"✓ Reached end of articles (got {len(article_list)} < {count})")
                        break

                    # Update offset for next page
                    offset += len(article_list)

                    # Rate limiting - be respectful to Pocket's servers
                    time.sleep(1)
                    
                elif response.status_code == 401:
                    raise Exception("Authentication failed. Token may be expired. Try re-authenticating.")
                elif response.status_code == 403:
                    raise Exception("Access forbidden. Check your consumer key and permissions.")
                elif response.status_code == 503:
                    print("⚠️  Pocket API temporarily unavailable, waiting 5 seconds...")
                    time.sleep(5)
                    continue
                else:
                    raise Exception(f"API request failed with status {response.status_code}: {response.text}")
                    
            except requests.RequestException as e:
                raise Exception(f"Network error retrieving articles: {e}")

        print(f"\n✓ Retrieval completed!")
        print(f"Total requests: {total_requests}")
        print(f"Total articles retrieved: {len(all_articles)}")
        
        # Convert back to Pocket's expected format
        return {"list": {article['item_id']: article for article in all_articles}}
        
    def get_article_details(self, item_id):
        """Get detailed information for a specific article."""
        if not self.access_token:
            raise Exception("Not authenticated. Call authenticate() first.")
            
        data = {
            "consumer_key": self.auth.consumer_key,
            "access_token": self.access_token,
            "detailType": "complete",
            "search": item_id
        }

        try:
            response = requests.post(RETRIEVE_URL, data=data, verify=True)
            if response.status_code == 200:
                result = response.json()
                articles = result.get('list', {})
                return articles.get(item_id)
            else:
                raise Exception(f"Failed to get article details: {response.text}")
        except requests.RequestException as e:
            raise Exception(f"Network error getting article details: {e}")
            
    def test_connection(self):
        """Test API connection by retrieving a small number of articles."""
        if not self.access_token:
            raise Exception("Not authenticated. Call authenticate() first.")
            
        print("Testing Pocket API connection...")
        
        try:
            # Try to get just 1 article to test connection
            data = {
                "consumer_key": self.auth.consumer_key,
                "access_token": self.access_token,
                "count": 1,
                "detailType": "simple"
            }

            response = requests.post(RETRIEVE_URL, data=data, verify=True)
            if response.status_code == 200:
                result = response.json()
                articles = result.get('list', {})
                print(f"✓ Connection successful! Found {len(articles)} article(s)")
                return True
            else:
                print(f"✗ Connection failed: {response.status_code} - {response.text}")
                return False
        except requests.RequestException as e:
            print(f"✗ Network error: {e}")
            return False


def main():
    """Test client functionality."""
    import sys
    
    client = PocketClient()
    
    try:
        # Authenticate
        print("Authenticating...")
        client.authenticate()
        
        # Test connection
        if not client.test_connection():
            sys.exit(1)
            
        # Get a small sample
        if len(sys.argv) > 1 and sys.argv[1] == "sample":
            print("\nRetrieving sample articles...")
            articles = client.retrieve_articles(count=5)
            
            print(f"\nSample articles:")
            for item_id, article in articles['list'].items():
                title = article.get('resolved_title', article.get('given_title', 'No title'))
                url = article.get('resolved_url', article.get('given_url', ''))
                print(f"- {title[:50]}...")
                print(f"  URL: {url}")
                print()
        else:
            print("Use 'python client.py sample' to retrieve sample articles")
            
    except Exception as e:
        print(f"Client test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()