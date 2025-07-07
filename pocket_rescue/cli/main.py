#!/usr/bin/env python3
"""
Pocket Rescue - Master CLI script for preserving Pocket articles.
Orchestrates the entire article preservation workflow with new API integration.
"""

import sys
import os
import subprocess
import time
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from pocket_rescue.utils.console_utils import init_console
    init_console()
except ImportError:
    pass


class PocketRescueCLI:
    def __init__(self, csv_file="part_000000.csv"):
        self.csv_file = csv_file
        self.base_dir = Path("saved_articles")
        
        # Update script paths to new package structure
        self.scripts = {
            'link_checker': 'pocket_rescue.core.link_checker',
            'content_scraper': 'pocket_rescue.core.content_scraper',
            'wayback_scraper': 'pocket_rescue.core.wayback_scraper',
            'priority_filter': 'pocket_rescue.core.priority_filter',
            'reading_tracker': 'pocket_rescue.core.reading_tracker',
            'content_organizer': 'pocket_rescue.core.content_organizer'
        }
        
    def run_module(self, module_name, args=None):
        """Run a module with optional arguments."""
        if module_name not in self.scripts:
            print(f"ERROR: Unknown module: {module_name}")
            return False
            
        module_path = self.scripts[module_name]
        cmd = [sys.executable, '-m', module_path]
        if args:
            cmd.extend(args)
            
        try:
            print(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
            
            if result.returncode == 0:
                print(f"OK: {module_name} completed successfully")
                if result.stdout:
                    print(result.stdout)
                return True
            else:
                print(f"ERROR: {module_name} failed with code {result.returncode}")
                if result.stderr:
                    print(f"Error: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"TIMEOUT: {module_name} timed out")
            return False
        except Exception as e:
            print(f"ERROR: Error running {module_name}: {e}")
            return False
            
    def fetch_from_api(self, count=30, state="all", save_raw=False):
        """Fetch articles directly from Pocket API."""
        print("Fetching articles from Pocket API")
        print("=" * 50)
        
        try:
            from pocket_rescue.api.client import PocketClient
            from pocket_rescue.api.processor import PocketProcessor
            
            # Initialize client and authenticate
            client = PocketClient()
            print("Authenticating with Pocket API...")
            client.authenticate()
            
            # Test connection
            if not client.test_connection():
                print("ERROR: Failed to connect to Pocket API")
                return False
                
            # Retrieve articles
            print(f"\nRetrieving articles (count={count}, state={state})...")
            articles_response = client.retrieve_articles(count=count, state=state)
            
            # Process and save
            processor = PocketProcessor()
            
            # Save raw JSON if requested
            if save_raw:
                processor.save_raw_json(articles_response)
                
            # Process articles
            filtered_articles = processor.process_articles(articles_response)
            
            # Show statistics
            processor.print_statistics(filtered_articles)
            
            # Save to CSV
            csv_file = processor.save_to_csv(filtered_articles, self.csv_file)
            
            if csv_file:
                print(f"\n✓ API fetch completed successfully!")
                print(f"✓ Articles saved to: {csv_file}")
                print(f"✓ Ready to use with: python pocket_rescue.py full-rescue")
                return True
            else:
                print("ERROR: Failed to save articles to CSV")
                return False
                
        except ImportError as e:
            print(f"ERROR: API modules not available: {e}")
            return False
        except Exception as e:
            print(f"ERROR: API fetch failed: {e}")
            return False
            
    def full_rescue_workflow(self, skip_archived=True, max_workers=10):
        """Execute the complete rescue workflow."""
        print("Starting Pocket Rescue Workflow")
        print("=" * 50)
        print(f"CSV file: {self.csv_file}")
        print(f"Skip archived: {skip_archived}")
        print(f"Max workers: {max_workers}")
        print(f"Started: {datetime.now()}")
        print()
        
        # Step 1: Check links (optional - for analysis)
        print("Step 1: Analyzing links...")
        args = [self.csv_file]
        if not skip_archived:
            args.append("--include-archived")
        self.run_module('link_checker', args)
        
        # Step 2: Scrape content from valid URLs
        print("\nStep 2: Scraping article content...")
        args = [self.csv_file, "--workers", str(max_workers)]
        if not skip_archived:
            args.append("--include-archived")
        success = self.run_module('content_scraper', args)
        
        if not success:
            print("WARNING: Content scraping failed. Continuing with other steps...")
            
        # Step 3: Try Wayback Machine for failed URLs
        invalid_links_file = "invalid_links.csv"
        if Path(invalid_links_file).exists():
            print(f"\nStep 3: Trying Wayback Machine for failed URLs...")
            self.run_module('wayback_scraper', [invalid_links_file])
        else:
            print("\nStep 3: No invalid links file found, skipping Wayback Machine")
            
        # Step 4: Organize content
        print("\nStep 4: Organizing content...")
        self.run_module('content_organizer', ['organize'])
        self.run_module('content_organizer', ['index'])
        
        # Step 5: Generate priority analysis
        print("\nStep 5: Analyzing priorities...")
        self.run_module('priority_filter', ['analyze', self.csv_file])
        
        # Export prioritized list
        priority_file = "priority_articles.csv"
        self.run_module('priority_filter', ['export', self.csv_file, priority_file])
        
        # Step 6: Show statistics
        print("\nStep 6: Generating statistics...")
        self.run_module('content_organizer', ['stats'])
        self.run_module('reading_tracker', ['stats'])
        
        print("\nRescue workflow completed!")
        print(f"Finished: {datetime.now()}")
        print(f"Content saved to: {self.base_dir}")
        
    def quick_rescue(self, priority_only=True):
        """Quick rescue for high-priority articles only."""
        print("Quick Rescue Mode - High Priority Articles Only")
        print("=" * 50)
        
        # Filter high priority articles first
        filtered_csv = "high_priority_articles.csv"
        args = ['filter', self.csv_file, '--priority', 'high,critical', '--status', 'unread', '--limit', '100']
        
        if self.run_module('priority_filter', args):
            # Export filtered list
            export_args = ['export', self.csv_file, filtered_csv]
            self.run_module('priority_filter', export_args)
            
            # Scrape only high priority articles
            if Path(filtered_csv).exists():
                print(f"\nScraping high priority articles...")
                self.run_module('content_scraper', [filtered_csv, '--workers', '5'])
                
                print("\nOrganizing content...")
                self.run_module('content_organizer', ['organize'])
                self.run_module('content_organizer', ['index'])
                
                print("\nQuick rescue completed!")
            else:
                print("ERROR: No high priority articles found")
        else:
            print("ERROR: Priority filtering failed")
            
    def create_reading_plan(self, daily_minutes=30):
        """Create a reading plan based on priorities."""
        print(f"Creating reading plan ({daily_minutes} minutes/day)")
        self.run_module('priority_filter', ['plan', self.csv_file, str(daily_minutes)])
        
    def search_articles(self, query):
        """Search saved articles."""
        print(f"Searching for: {query}")
        self.run_module('content_organizer', ['search', query])
        
    def show_help(self):
        """Show help information."""
        print("""
Pocket Rescue - Help

Usage: python pocket_rescue.py <command> [options]

Commands:
  fetch-from-api [--count N] [--state unread|archive|all] [--save-raw]
    Fetch articles directly from Pocket API (eliminates manual CSV export)
    
  clear-auth
    Clear saved Pocket API authentication tokens (force re-authentication)
    
  full-rescue [--include-archived] [--workers N]
    Complete rescue workflow: check links, scrape content, organize, prioritize
    
  quick-rescue
    Rescue only high-priority unread articles (faster)
    
  check-links [--include-archived]
    Check URL validity and create invalid links report
    
  scrape-content [--include-archived] [--workers N]
    Scrape article content from valid URLs
    
  wayback-rescue <invalid_links.csv>
    Try to recover content from Wayback Machine
    
  organize
    Organize saved articles into category folders
    
  prioritize
    Analyze and prioritize articles
    
  reading-plan [--daily-minutes N]
    Create personalized reading plan
    
  search <query>
    Search saved articles
    
  stats
    Show statistics about saved content

New API Workflow:
  python pocket_rescue.py fetch-from-api
  python pocket_rescue.py full-rescue
    
Traditional Workflow:
  python pocket_rescue.py full-rescue --workers 20
  python pocket_rescue.py quick-rescue
  python pocket_rescue.py reading-plan --daily-minutes 45
  python pocket_rescue.py search "python programming"
  python pocket_rescue.py stats
        """)


def main():
    if len(sys.argv) < 2:
        rescue = PocketRescueCLI()
        rescue.show_help()
        return
        
    command = sys.argv[1]
    rescue = PocketRescueCLI()
    
    if command == "fetch-from-api":
        count = 30
        state = "all"
        save_raw = "--save-raw" in sys.argv
        
        if "--count" in sys.argv:
            try:
                idx = sys.argv.index("--count")
                count = int(sys.argv[idx + 1])
            except (IndexError, ValueError):
                print("ERROR: Invalid --count value")
                return
                
        if "--state" in sys.argv:
            try:
                idx = sys.argv.index("--state")
                state = sys.argv[idx + 1]
                if state not in ["unread", "archive", "all"]:
                    print("ERROR: --state must be unread, archive, or all")
                    return
            except IndexError:
                print("ERROR: Missing --state value")
                return
                
        rescue.fetch_from_api(count, state, save_raw)
        
    elif command == "clear-auth":
        try:
            from pocket_rescue.api.auth import PocketAuth
            auth = PocketAuth()
            auth.clear_tokens()
        except ImportError as e:
            print(f"ERROR: API modules not available: {e}")
        except Exception as e:
            print(f"ERROR: Failed to clear tokens: {e}")
            
    elif command == "full-rescue":
        skip_archived = "--include-archived" not in sys.argv
        max_workers = 10
        
        if "--workers" in sys.argv:
            try:
                idx = sys.argv.index("--workers")
                max_workers = int(sys.argv[idx + 1])
            except (IndexError, ValueError):
                print("ERROR: Invalid --workers value")
                return
                
        rescue.full_rescue_workflow(skip_archived, max_workers)
        
    elif command == "quick-rescue":
        rescue.quick_rescue()
        
    elif command == "check-links":
        args = [rescue.csv_file]
        if "--include-archived" in sys.argv:
            args.append("--include-archived")
        rescue.run_module('link_checker', args)
        
    elif command == "scrape-content":
        args = [rescue.csv_file]
        if "--include-archived" in sys.argv:
            args.append("--include-archived")
        if "--workers" in sys.argv:
            try:
                idx = sys.argv.index("--workers")
                args.extend(["--workers", sys.argv[idx + 1]])
            except (IndexError, ValueError):
                print("ERROR: Invalid --workers value")
                return
        rescue.run_module('content_scraper', args)
        
    elif command == "wayback-rescue" and len(sys.argv) >= 3:
        invalid_file = sys.argv[2]
        rescue.run_module('wayback_scraper', [invalid_file])
        
    elif command == "organize":
        rescue.run_module('content_organizer', ['organize'])
        rescue.run_module('content_organizer', ['index'])
        
    elif command == "prioritize":
        rescue.run_module('priority_filter', ['analyze', rescue.csv_file])
        
    elif command == "reading-plan":
        daily_minutes = 30
        if "--daily-minutes" in sys.argv:
            try:
                idx = sys.argv.index("--daily-minutes")
                daily_minutes = int(sys.argv[idx + 1])
            except (IndexError, ValueError):
                print("ERROR: Invalid --daily-minutes value")
                return
        rescue.create_reading_plan(daily_minutes)
        
    elif command == "search" and len(sys.argv) >= 3:
        query = ' '.join(sys.argv[2:])
        rescue.search_articles(query)
        
    elif command == "stats":
        rescue.run_module('content_organizer', ['stats'])
        rescue.run_module('reading_tracker', ['stats'])
        
    else:
        print(f"ERROR: Unknown command: {command}")
        rescue.show_help()


if __name__ == "__main__":
    main()