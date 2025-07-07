#!/usr/bin/env python3
"""
Pocket API OAuth authentication module.
Handles the 3-step OAuth flow for Pocket API access.
"""

import requests
import webbrowser
import os
import time
from urllib.parse import urlencode
from pathlib import Path
import json

# Pocket API endpoints
REQUEST_TOKEN_URL = "https://getpocket.com/v3/oauth/request"
AUTHORIZE_URL = "https://getpocket.com/auth/authorize"
ACCESS_TOKEN_URL = "https://getpocket.com/v3/oauth/authorize"

# Default consumer key from reference implementation
DEFAULT_CONSUMER_KEY = "116449-e065de795cc07ddf9c37783"


class PocketAuth:
    def __init__(self, consumer_key=None):
        """Initialize Pocket authentication."""
        self.consumer_key = consumer_key or os.getenv('POCKET_CONSUMER_KEY', DEFAULT_CONSUMER_KEY)
        if not self.consumer_key:
            raise ValueError("Consumer key is required. Set POCKET_CONSUMER_KEY environment variable or pass consumer_key parameter.")
        self.config_dir = Path.home() / '.pocket_rescue'
        self.config_file = self.config_dir / 'auth.json'
        self.config_dir.mkdir(exist_ok=True)
        
    def get_request_token(self):
        """Get a request token from Pocket."""
        data = {
            "consumer_key": self.consumer_key,
            "redirect_uri": "pocketapp1234:authorizationFinished"
        }

        try:
            response = requests.post(REQUEST_TOKEN_URL, data=data, verify=True)
            if response.status_code == 200:
                return response.text.split('=')[1]
            else:
                raise Exception(f"Failed to get request token: HTTP {response.status_code} - {response.text}")
        except requests.RequestException as e:
            raise Exception(f"Network error getting request token: {e}")

    def authorize_app(self, request_token):
        """Open browser for user authorization."""
        auth_url = f"{AUTHORIZE_URL}?{urlencode({'request_token': request_token, 'redirect_uri': 'pocketapp1234:authorizationFinished'})}"
        
        print(f"Opening browser for authorization...")
        print(f"URL: {auth_url}")
        print()
        print("📋 AUTHORIZATION STEPS:")
        print("1. Click 'Authorize' in the browser window that opened")
        print("2. Wait for the page to show 'Authorization complete' or similar")
        print("3. The browser window may not close automatically - that's OK")
        print("4. Return here and press Enter only AFTER you see authorization confirmed")
        print()
        
        try:
            webbrowser.open(auth_url)
        except Exception as e:
            print(f"Failed to open browser automatically: {e}")
            print(f"Please manually open this URL: {auth_url}")
            
        input("✅ Press Enter ONLY after you've completed authorization in your browser...")

    def get_access_token(self, request_token):
        """Exchange request token for access token."""
        data = {
            "consumer_key": self.consumer_key,
            "code": request_token
        }

        # Add a small delay to ensure authorization is processed
        print("⏳ Waiting a moment for authorization to be processed...")
        time.sleep(2)

        try:
            response = requests.post(ACCESS_TOKEN_URL, data=data, verify=True)
            if response.status_code == 200:
                # Parse the response more carefully
                response_text = response.text
                if 'access_token=' in response_text:
                    access_token = response_text.split('access_token=')[1].split('&')[0]
                    return access_token
                else:
                    # Fallback to original parsing
                    return response_text.split('&')[0].split('=')[1]
            elif response.status_code == 403:
                raise Exception("Authorization denied. Please make sure you clicked 'Authorize' in the browser.")
            elif response.status_code == 500:
                raise Exception("Pocket server error. This may happen if authorization wasn't completed properly. Please try again and make sure to complete authorization in the browser.")
            else:
                raise Exception(f"Failed to get access token: HTTP {response.status_code} - {response.text}")
        except requests.RequestException as e:
            raise Exception(f"Network error getting access token: {e}")

    def save_tokens(self, access_token, request_token=None):
        """Save tokens to config file."""
        config = {
            'access_token': access_token,
            'consumer_key': self.consumer_key
        }
        if request_token:
            config['request_token'] = request_token
            
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            print(f"Tokens saved to: {self.config_file}")
        except Exception as e:
            print(f"Warning: Failed to save tokens: {e}")

    def load_tokens(self):
        """Load tokens from config file."""
        if not self.config_file.exists():
            return None
            
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            return config.get('access_token')
        except Exception as e:
            print(f"Warning: Failed to load saved tokens: {e}")
            return None

    def authenticate(self, force_reauth=False):
        """Complete authentication flow and return access token."""
        # Try to load existing token first
        if not force_reauth:
            existing_token = self.load_tokens()
            if existing_token:
                print("Using saved access token")
                return existing_token

        print("Starting Pocket API authentication...")
        print("=" * 50)
        
        try:
            # Step 1: Get request token
            print("Step 1: Getting request token...")
            request_token = self.get_request_token()
            print(f"✓ Request token obtained")

            # Step 2: Authorize the app
            print("\nStep 2: User authorization...")
            self.authorize_app(request_token)

            # Step 3: Get access token
            print("\nStep 3: Getting access token...")
            access_token = self.get_access_token(request_token)
            print(f"✓ Access token obtained")

            # Save tokens for future use
            self.save_tokens(access_token, request_token)
            
            print("\n✓ Authentication completed successfully!")
            return access_token
            
        except Exception as e:
            print(f"\n✗ Authentication failed: {e}")
            raise

    def clear_tokens(self):
        """Clear saved authentication tokens."""
        if self.config_file.exists():
            try:
                self.config_file.unlink()
                print("Saved tokens cleared")
            except Exception as e:
                print(f"Failed to clear tokens: {e}")
        else:
            print("No saved tokens found")


def main():
    """Test authentication flow."""
    import sys
    
    auth = PocketAuth()
    
    if len(sys.argv) > 1 and sys.argv[1] == "clear":
        auth.clear_tokens()
        return
        
    try:
        access_token = auth.authenticate()
        print(f"\nAccess token: {access_token[:20]}...")
        print("Authentication test completed successfully!")
    except Exception as e:
        print(f"Authentication test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()