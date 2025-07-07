#!/usr/bin/env python3
"""
Article content scraper for Pocket articles.
Downloads full article content and saves to local files.
"""

import csv
import requests
import os
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import re
import hashlib

# For article extraction
try:
    from newspaper import Article
    NEWSPAPER_AVAILABLE = True
except ImportError:
    NEWSPAPER_AVAILABLE = False

try:
    from readability import Document
    READABILITY_AVAILABLE = True
except ImportError:
    READABILITY_AVAILABLE = False

from bs4 import BeautifulSoup


class ContentScraper:
    def __init__(self, base_dir="saved_articles"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        self.db_path = self.base_dir / "articles.db"
        self.init_database()
        
    def init_database(self):
        """Initialize SQLite database for tracking articles."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
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
                success BOOLEAN DEFAULT 0
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def clean_filename(self, title, url):
        """Create safe filename from title and URL."""
        if not title or title.strip() == "":
            title = urlparse(url).netloc
            
        # Remove invalid characters
        cleaned = re.sub(r'[<>:"/\\|?*]', '', title)
        cleaned = re.sub(r'\s+', '_', cleaned.strip())
        
        # Limit length and add hash for uniqueness
        if len(cleaned) > 100:
            cleaned = cleaned[:100]
            
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        return f"{cleaned}_{url_hash}"
        
    def extract_with_newspaper(self, url):
        """Extract article content using newspaper3k."""
        if not NEWSPAPER_AVAILABLE:
            return None, None, "newspaper3k not available"
            
        try:
            article = Article(url)
            article.download()
            article.parse()
            
            return article.text, article.title, None
        except Exception as e:
            return None, None, f"Newspaper error: {str(e)}"
            
    def extract_with_readability(self, url):
        """Extract article content using readability."""
        if not READABILITY_AVAILABLE:
            return None, None, "readability not available"
            
        try:
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response.raise_for_status()
            
            doc = Document(response.text)
            title = doc.title()
            content = doc.summary()
            
            # Convert HTML to text
            soup = BeautifulSoup(content, 'html.parser')
            text = soup.get_text(separator='\n', strip=True)
            
            return text, title, None
        except Exception as e:
            return None, None, f"Readability error: {str(e)}"
            
    def extract_with_basic_scraping(self, url):
        """Basic HTML scraping fallback."""
        try:
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
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
            return None, None, f"Basic scraping error: {str(e)}"
            
    def scrape_article(self, row):
        """Scrape a single article using multiple methods."""
        url = row['url']
        original_title = row['title']
        
        # Try different extraction methods
        methods = [
            ("newspaper", self.extract_with_newspaper),
            ("readability", self.extract_with_readability),
            ("basic", self.extract_with_basic_scraping)
        ]
        
        for method_name, method_func in methods:
            content, title, error = method_func(url)
            if content and len(content.strip()) > 100:  # Minimum content length
                break
        else:
            return {
                'url': url,
                'success': False,
                'error': 'All extraction methods failed',
                'method': 'none'
            }
            
        # Use original title if extracted title is empty
        if not title or title.strip() == "":
            title = original_title
            
        # Create filename and save content
        filename = self.clean_filename(title, url)
        
        # Create folder structure based on tags
        tags = row.get('tags', '')
        if tags:
            # Use first tag as folder name
            folder_name = tags.split('|')[0].strip()
            folder_name = re.sub(r'[<>:"/\\|?*]', '', folder_name)
            article_dir = self.base_dir / folder_name
        else:
            article_dir = self.base_dir / "untagged"
            
        article_dir.mkdir(exist_ok=True)
        
        # Save as markdown
        file_path = article_dir / f"{filename}.md"
        
        markdown_content = f"""# {title}

**URL:** {url}
**Tags:** {tags}
**Date Added:** {datetime.fromtimestamp(int(row.get('time_added', 0)))}
**Status:** {row.get('status', 'unread')}

---

{content}
"""
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
            
        # Estimate reading time (average 200 words per minute)
        word_count = len(content.split())
        reading_time = max(1, word_count // 200)
        
        # Save to database
        self.save_to_database(row, title, file_path, len(content), reading_time, method_name)
        
        return {
            'url': url,
            'title': title,
            'file_path': str(file_path),
            'content_length': len(content),
            'reading_time': reading_time,
            'method': method_name,
            'success': True
        }
        
    def save_to_database(self, row, title, file_path, content_length, reading_time, method):
        """Save article info to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO articles 
            (url, title, status, tags, time_added, time_scraped, file_path, 
             content_length, reading_time_estimate, scrape_method, success)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            method,
            True
        ))
        
        conn.commit()
        conn.close()
        
    def process_csv(self, csv_file, max_workers=10, skip_archived=True):
        """Process CSV file and scrape articles."""
        print(f"Processing: {csv_file}")
        print(f"Skip archived: {skip_archived}")
        print(f"Max workers: {max_workers}")
        print("-" * 50)
        
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            all_rows = list(reader)
            
        # Filter rows
        if skip_archived:
            rows = [row for row in all_rows if row.get('status', '').lower() != 'archive']
            print(f"Skipped {len(all_rows) - len(rows)} archived entries")
        else:
            rows = all_rows
            
        print(f"Processing {len(rows)} articles")
        
        successful = 0
        failed = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_row = {executor.submit(self.scrape_article, row): row for row in rows}
            
            for i, future in enumerate(as_completed(future_to_row), 1):
                try:
                    result = future.result()
                    if result['success']:
                        successful += 1
                        print(f"OK [{i}/{len(rows)}] {result['title'][:60]}...")
                    else:
                        failed += 1
                        print(f"ERROR [{i}/{len(rows)}] {result['url']} - {result['error']}")
                except Exception as e:
                    failed += 1
                    print(f"ERROR [{i}/{len(rows)}] Unexpected error: {str(e)}")
                    
        print(f"\nCompleted: {successful} successful, {failed} failed")
        print(f"Articles saved to: {self.base_dir}")
        print(f"Database: {self.db_path}")


def main():
    import sys
    
    csv_file = "part_000000.csv"
    max_workers = 10
    skip_archived = True
    
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    if "--include-archived" in sys.argv:
        skip_archived = False
    if "--workers" in sys.argv:
        idx = sys.argv.index("--workers")
        if idx + 1 < len(sys.argv):
            max_workers = int(sys.argv[idx + 1])
            
    scraper = ContentScraper()
    scraper.process_csv(csv_file, max_workers, skip_archived)


if __name__ == "__main__":
    main()