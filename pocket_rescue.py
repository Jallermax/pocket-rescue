#!/usr/bin/env python3
"""
Pocket Rescue - Master script for preserving Pocket articles.
Orchestrates the entire article preservation workflow.
"""

import sys
import os
import subprocess
import time
from pathlib import Path
from datetime import datetime

# Setup console encoding for Windows compatibility
try:
    from console_utils import init_console
    init_console()
except ImportError:
    pass


class PocketRescue:
    def __init__(self, csv_file="part_000000.csv"):
        self.csv_file = csv_file
        self.base_dir = Path("saved_articles")
        self.scripts = {
            'check_links': 'check_links.py',
            'content_scraper': 'content_scraper.py',
            'wayback_scraper': 'wayback_scraper.py',
            'priority_filter': 'priority_filter.py',
            'reading_tracker': 'reading_tracker.py',
            'content_organizer': 'content_organizer.py'
        }
        
    def run_script(self, script_name, args=None):
        """Run a script with optional arguments."""
        if script_name not in self.scripts:
            print(f"ERROR: Unknown script: {script_name}")
            return False
            
        script_path = self.scripts[script_name]
        if not Path(script_path).exists():
            print(f"ERROR: Script not found: {script_path}")
            return False
            
        cmd = [sys.executable, script_path]
        if args:
            cmd.extend(args)
            
        try:
            print(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
            
            if result.returncode == 0:
                print(f"OK: {script_name} completed successfully")
                if result.stdout:
                    print(result.stdout)
                return True
            else:
                print(f"ERROR: {script_name} failed with code {result.returncode}")
                if result.stderr:
                    print(f"Error: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"TIMEOUT: {script_name} timed out")
            return False
        except Exception as e:
            print(f"ERROR: Error running {script_name}: {e}")
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
        self.run_script('check_links', args)
        
        # Step 2: Scrape content from valid URLs
        print("\nStep 2: Scraping article content...")
        args = [self.csv_file, "--workers", str(max_workers)]
        if not skip_archived:
            args.append("--include-archived")
        success = self.run_script('content_scraper', args)
        
        if not success:
            print("WARNING: Content scraping failed. Continuing with other steps...")
            
        # Step 3: Try Wayback Machine for failed URLs
        invalid_links_file = "invalid_links.csv"
        if Path(invalid_links_file).exists():
            print(f"\nStep 3: Trying Wayback Machine for failed URLs...")
            self.run_script('wayback_scraper', [invalid_links_file])
        else:
            print("\nStep 3: No invalid links file found, skipping Wayback Machine")
            
        # Step 4: Organize content
        print("\nStep 4: Organizing content...")
        self.run_script('content_organizer', ['organize'])
        self.run_script('content_organizer', ['index'])
        
        # Step 5: Generate priority analysis
        print("\nStep 5: Analyzing priorities...")
        self.run_script('priority_filter', ['analyze', self.csv_file])
        
        # Export prioritized list
        priority_file = "priority_articles.csv"
        self.run_script('priority_filter', ['export', self.csv_file, priority_file])
        
        # Step 6: Show statistics
        print("\nStep 6: Generating statistics...")
        self.run_script('content_organizer', ['stats'])
        self.run_script('reading_tracker', ['stats'])
        
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
        
        if self.run_script('priority_filter', args):
            # Export filtered list
            export_args = ['export', self.csv_file, filtered_csv]
            self.run_script('priority_filter', export_args)
            
            # Scrape only high priority articles
            if Path(filtered_csv).exists():
                print(f"\nScraping high priority articles...")
                self.run_script('content_scraper', [filtered_csv, '--workers', '5'])
                
                print("\nOrganizing content...")
                self.run_script('content_organizer', ['organize'])
                self.run_script('content_organizer', ['index'])
                
                print("\nQuick rescue completed!")
            else:
                print("ERROR: No high priority articles found")
        else:
            print("ERROR: Priority filtering failed")
            
    def create_reading_plan(self, daily_minutes=30):
        """Create a reading plan based on priorities."""
        print(f"Creating reading plan ({daily_minutes} minutes/day)")
        self.run_script('priority_filter', ['plan', self.csv_file, str(daily_minutes)])
        
    def search_articles(self, query):
        """Search saved articles."""
        print(f"Searching for: {query}")
        self.run_script('content_organizer', ['search', query])
        
    def show_help(self):
        """Show help information."""
        print("""
Pocket Rescue - Help

Usage: python pocket_rescue.py <command> [options]

Commands:
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
    
Examples:
  python pocket_rescue.py full-rescue --workers 20
  python pocket_rescue.py quick-rescue
  python pocket_rescue.py reading-plan --daily-minutes 45
  python pocket_rescue.py search "python programming"
  python pocket_rescue.py stats
        """)


def main():
    if len(sys.argv) < 2:
        rescue = PocketRescue()
        rescue.show_help()
        return
        
    command = sys.argv[1]
    rescue = PocketRescue()
    
    if command == "full-rescue":
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
        rescue.run_script('check_links', args)
        
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
        rescue.run_script('content_scraper', args)
        
    elif command == "wayback-rescue" and len(sys.argv) >= 3:
        invalid_file = sys.argv[2]
        rescue.run_script('wayback_scraper', [invalid_file])
        
    elif command == "organize":
        rescue.run_script('content_organizer', ['organize'])
        rescue.run_script('content_organizer', ['index'])
        
    elif command == "prioritize":
        rescue.run_script('priority_filter', ['analyze', rescue.csv_file])
        
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
        rescue.run_script('content_organizer', ['stats'])
        rescue.run_script('reading_tracker', ['stats'])
        
    else:
        print(f"ERROR: Unknown command: {command}")
        rescue.show_help()


if __name__ == "__main__":
    main()