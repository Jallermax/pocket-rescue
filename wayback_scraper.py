#!/usr/bin/env python3
"""
Wayback Machine integration for retrieving content from dead/invalid links.
"""

import requests
import json
import time
from datetime import datetime
from urllib.parse import quote
import sqlite3
from pathlib import Path
import re
import hashlib
from bs4 import BeautifulSoup


class WaybackScraper:
    def __init__(self, base_dir="saved_articles"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        self.db_path = self.base_dir / "articles.db"
        self.wayback_api = "http://web.archive.org/cdx/search/cdx"
        self.wayback_base = "http://web.archive.org/web"
        
    def search_wayback_snapshots(self, url, limit=5):
        """Search for available snapshots of a URL in Wayback Machine."""
        try:
            params = {
                'url': url,
                'output': 'json',
                'limit': limit,
                'filter': 'statuscode:200',
                'sort': 'timestamp',
                'order': 'desc'
            }
            
            response = requests.get(self.wayback_api, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if len(data) <= 1:  # Only header row
                return []
                
            snapshots = []
            for row in data[1:]:  # Skip header row
                snapshot = {
                    'timestamp': row[1],
                    'url': row[2],
                    'status': row[4],
                    'archive_url': f"{self.wayback_base}/{row[1]}/{row[2]}"
                }
                snapshots.append(snapshot)
                
            return snapshots
            
        except Exception as e:
            print(f"Error searching Wayback Machine for {url}: {str(e)}")
            return []
            
    def get_wayback_content(self, archive_url):
        """Retrieve content from Wayback Machine archive URL."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(archive_url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove Wayback Machine toolbar/navigation
            wayback_toolbar = soup.find('div', id='wm-ipp-base')
            if wayback_toolbar:
                wayback_toolbar.decompose()
                
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
                
            # Try to find main content
            content_selectors = [
                'article', 'main', '.content', '#content', 
                '.post', '.article', '.story', '.entry-content'
            ]
            
            content = None
            for selector in content_selectors:
                elements = soup.select(selector)
                if elements:
                    content = elements[0]
                    break
                    
            if not content:
                content = soup.body or soup
                
            title = soup.title.string if soup.title else ""
            text = content.get_text(separator='\n', strip=True)
            
            return text, title, None
            
        except Exception as e:
            return None, None, f"Wayback retrieval error: {str(e)}"
            
    def clean_filename(self, title, url):
        """Create safe filename from title and URL."""
        if not title or title.strip() == "":
            title = "archived_page"
            
        # Remove invalid characters
        cleaned = re.sub(r'[<>:"/\\|?*]', '', title)
        cleaned = re.sub(r'\s+', '_', cleaned.strip())
        
        # Limit length and add hash for uniqueness
        if len(cleaned) > 100:
            cleaned = cleaned[:100]
            
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        return f"{cleaned}_{url_hash}"
        
    def scrape_from_wayback(self, row):
        """Attempt to scrape article from Wayback Machine."""
        url = row['url']
        original_title = row['title']
        
        print(f"Searching Wayback Machine for: {url}")
        
        # Search for snapshots
        snapshots = self.search_wayback_snapshots(url)
        if not snapshots:
            return {
                'url': url,
                'success': False,
                'error': 'No Wayback Machine snapshots found',
                'method': 'wayback'
            }
            
        # Try to get content from the most recent snapshot
        for snapshot in snapshots:
            print(f"  Trying snapshot from {snapshot['timestamp']}")
            
            content, title, error = self.get_wayback_content(snapshot['archive_url'])
            if content and len(content.strip()) > 100:
                break
                
            time.sleep(1)  # Be respectful to Wayback Machine
        else:
            return {
                'url': url,
                'success': False,
                'error': 'Failed to extract content from any snapshot',
                'method': 'wayback'
            }
            
        # Use original title if extracted title is empty or just "Wayback Machine"
        if not title or title.strip() == "" or "Wayback Machine" in title:
            title = original_title or "Archived Article"
            
        # Create filename and save content
        filename = self.clean_filename(title, url)
        
        # Create wayback folder
        wayback_dir = self.base_dir / "wayback_archived"
        wayback_dir.mkdir(exist_ok=True)
        
        # Save as markdown
        file_path = wayback_dir / f"{filename}.md"
        
        snapshot_date = datetime.strptime(snapshot['timestamp'], '%Y%m%d%H%M%S')
        
        markdown_content = f"""# {title}

**Original URL:** {url}
**Archive URL:** {snapshot['archive_url']}
**Snapshot Date:** {snapshot_date.strftime('%Y-%m-%d %H:%M:%S')}
**Tags:** {row.get('tags', '')}
**Date Added to Pocket:** {datetime.fromtimestamp(int(row.get('time_added', 0)))}
**Status:** {row.get('status', 'unread')} (recovered from Wayback Machine)

---

{content}
"""
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
            
        # Estimate reading time
        word_count = len(content.split())
        reading_time = max(1, word_count // 200)
        
        # Save to database
        self.save_to_database(row, title, file_path, len(content), reading_time, snapshot['archive_url'])
        
        return {
            'url': url,
            'title': title,
            'file_path': str(file_path),
            'content_length': len(content),
            'reading_time': reading_time,
            'method': 'wayback',
            'snapshot_date': snapshot_date.isoformat(),
            'archive_url': snapshot['archive_url'],
            'success': True
        }
        
    def save_to_database(self, row, title, file_path, content_length, reading_time, archive_url):
        """Save article info to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE,
                title TEXT,
                status TEXT DEFAULT 'unread',
                tags TEXT,
                time_added INTEGER,
                time_scraped INTEGER,
                file_path TEXT,
                content_length INTEGER,
                reading_time_estimate INTEGER,
                scrape_method TEXT,
                archive_url TEXT,
                success BOOLEAN DEFAULT 0
            )
        ''')
        
        # Add archive_url column if it doesn't exist (migration)
        try:
            cursor.execute('ALTER TABLE articles ADD COLUMN archive_url TEXT')
        except sqlite3.OperationalError:
            # Column already exists
            pass
        
        cursor.execute('''
            INSERT OR REPLACE INTO articles 
            (url, title, status, tags, time_added, time_scraped, file_path, 
             content_length, reading_time_estimate, scrape_method, archive_url, success)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            row['url'],
            title,
            row.get('status', 'unread'),
            row.get('tags', ''),
            int(row.get('time_added', 0)),
            int(time.time()),
            str(file_path),
            content_length,
            reading_time,
            'wayback',
            archive_url,
            True
        ))
        
        conn.commit()
        conn.close()
        
    def process_failed_urls(self, failed_urls_file):
        """Process URLs that failed in the original scraping."""
        import csv
        
        print(f"Processing failed URLs from: {failed_urls_file}")
        
        with open(failed_urls_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            failed_rows = list(reader)
            
        print(f"Found {len(failed_rows)} failed URLs to try with Wayback Machine")
        
        successful = 0
        failed = 0
        
        for i, row in enumerate(failed_rows, 1):
            print(f"\n[{i}/{len(failed_rows)}] Processing: {row['url']}")
            
            try:
                result = self.scrape_from_wayback(row)
                if result['success']:
                    successful += 1
                    print(f"OK Recovered: {result['title'][:60]}...")
                else:
                    failed += 1
                    print(f"ERROR Failed: {result['error']}")
            except Exception as e:
                failed += 1
                print(f"ERROR Unexpected error: {str(e)}")
                
            # Be respectful to Wayback Machine
            time.sleep(2)
            
        print(f"\nWayback recovery completed: {successful} successful, {failed} failed")
        print(f"Articles saved to: {self.base_dir / 'wayback_archived'}")


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python wayback_scraper.py <failed_urls_csv>")
        print("Example: python wayback_scraper.py invalid_links.csv")
        sys.exit(1)
        
    failed_urls_file = sys.argv[1]
    
    scraper = WaybackScraper()
    scraper.process_failed_urls(failed_urls_file)


if __name__ == "__main__":
    main()