#!/usr/bin/env python3
"""
Reading progress tracker for saved articles.
Manages reading status and provides statistics.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
import csv


class ReadingTracker:
    def __init__(self, base_dir="saved_articles"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        self.db_path = self.base_dir / "articles.db"
        self.init_database()
        
    def init_database(self):
        """Initialize or upgrade database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create articles table
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
        
        # Create reading progress table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reading_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id INTEGER,
                reading_status TEXT DEFAULT 'unread',
                progress_percent INTEGER DEFAULT 0,
                time_started INTEGER,
                time_completed INTEGER,
                notes TEXT,
                rating INTEGER,
                FOREIGN KEY (article_id) REFERENCES articles (id)
            )
        ''')
        
        # Create reading sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reading_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id INTEGER,
                session_start INTEGER,
                session_end INTEGER,
                duration_minutes INTEGER,
                notes TEXT,
                FOREIGN KEY (article_id) REFERENCES articles (id)
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def get_article_by_url(self, url):
        """Get article by URL."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM articles WHERE url = ?', (url,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
        return None
        
    def get_article_by_id(self, article_id):
        """Get article by ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM articles WHERE id = ?', (article_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
        return None
        
    def update_reading_status(self, article_id, status, progress=None, notes=None, rating=None):
        """Update reading status for an article."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get or create reading progress record
        cursor.execute('SELECT id FROM reading_progress WHERE article_id = ?', (article_id,))
        progress_row = cursor.fetchone()
        
        current_time = int(datetime.now().timestamp())
        
        if progress_row:
            # Update existing record
            update_fields = ['reading_status = ?']
            values = [status]
            
            if progress is not None:
                update_fields.append('progress_percent = ?')
                values.append(progress)
                
            if notes is not None:
                update_fields.append('notes = ?')
                values.append(notes)
                
            if rating is not None:
                update_fields.append('rating = ?')
                values.append(rating)
                
            if status == 'reading' and progress == 0:
                update_fields.append('time_started = ?')
                values.append(current_time)
            elif status == 'completed':
                update_fields.append('time_completed = ?')
                values.append(current_time)
                if progress is None:
                    update_fields.append('progress_percent = ?')
                    values.append(100)
                    
            values.append(progress_row[0])
            
            cursor.execute(f'''
                UPDATE reading_progress 
                SET {', '.join(update_fields)}
                WHERE id = ?
            ''', values)
        else:
            # Create new record
            time_started = current_time if status == 'reading' else None
            time_completed = current_time if status == 'completed' else None
            progress_percent = 100 if status == 'completed' else (progress or 0)
            
            cursor.execute('''
                INSERT INTO reading_progress 
                (article_id, reading_status, progress_percent, time_started, time_completed, notes, rating)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (article_id, status, progress_percent, time_started, time_completed, notes, rating))
            
        conn.commit()
        conn.close()
        
    def start_reading_session(self, article_id):
        """Start a new reading session."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        session_start = int(datetime.now().timestamp())
        
        cursor.execute('''
            INSERT INTO reading_sessions (article_id, session_start)
            VALUES (?, ?)
        ''', (article_id, session_start))
        
        session_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return session_id
        
    def end_reading_session(self, session_id, notes=None):
        """End a reading session."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        session_end = int(datetime.now().timestamp())
        
        # Get session start time
        cursor.execute('SELECT session_start FROM reading_sessions WHERE id = ?', (session_id,))
        row = cursor.fetchone()
        
        if row:
            session_start = row[0]
            duration_minutes = (session_end - session_start) // 60
            
            cursor.execute('''
                UPDATE reading_sessions 
                SET session_end = ?, duration_minutes = ?, notes = ?
                WHERE id = ?
            ''', (session_end, duration_minutes, notes, session_id))
            
        conn.commit()
        conn.close()
        
    def get_reading_stats(self):
        """Get reading statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total articles
        cursor.execute('SELECT COUNT(*) FROM articles WHERE success = 1')
        total_articles = cursor.fetchone()[0]
        
        # Articles by status
        cursor.execute('''
            SELECT 
                COALESCE(rp.reading_status, 'unread') as status,
                COUNT(*) as count
            FROM articles a
            LEFT JOIN reading_progress rp ON a.id = rp.article_id
            WHERE a.success = 1
            GROUP BY COALESCE(rp.reading_status, 'unread')
        ''')
        status_counts = dict(cursor.fetchall())
        
        # Total reading time
        cursor.execute('SELECT SUM(duration_minutes) FROM reading_sessions')
        total_reading_time = cursor.fetchone()[0] or 0
        
        # Average rating
        cursor.execute('SELECT AVG(rating) FROM reading_progress WHERE rating IS NOT NULL')
        avg_rating = cursor.fetchone()[0]
        
        # Top tags
        cursor.execute('''
            SELECT tags, COUNT(*) as count
            FROM articles 
            WHERE success = 1 AND tags IS NOT NULL AND tags != ''
            GROUP BY tags
            ORDER BY count DESC
            LIMIT 10
        ''')
        top_tags = cursor.fetchall()
        
        conn.close()
        
        return {
            'total_articles': total_articles,
            'by_status': status_counts,
            'total_reading_time_minutes': total_reading_time,
            'total_reading_time_hours': round(total_reading_time / 60, 1),
            'average_rating': round(avg_rating, 1) if avg_rating else None,
            'top_tags': top_tags
        }
        
    def get_reading_list(self, status='unread', limit=None, tag_filter=None):
        """Get articles by reading status."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = '''
            SELECT 
                a.id, a.url, a.title, a.tags, a.reading_time_estimate, a.file_path,
                COALESCE(rp.reading_status, 'unread') as reading_status,
                rp.progress_percent, rp.rating, rp.notes
            FROM articles a
            LEFT JOIN reading_progress rp ON a.id = rp.article_id
            WHERE a.success = 1
        '''
        
        params = []
        
        if status:
            query += ' AND COALESCE(rp.reading_status, \'unread\') = ?'
            params.append(status)
            
        if tag_filter:
            query += ' AND a.tags LIKE ?'
            params.append(f'%{tag_filter}%')
            
        query += ' ORDER BY a.time_added DESC'
        
        if limit:
            query += ' LIMIT ?'
            params.append(limit)
            
        cursor.execute(query, params)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        
        conn.close()
        
        return [dict(zip(columns, row)) for row in rows]
        
    def export_reading_data(self, output_file):
        """Export reading data to CSV."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                a.url, a.title, a.tags, a.reading_time_estimate, a.file_path,
                COALESCE(rp.reading_status, 'unread') as reading_status,
                rp.progress_percent, rp.rating, rp.notes,
                datetime(a.time_added, 'unixepoch') as date_added,
                datetime(rp.time_started, 'unixepoch') as date_started,
                datetime(rp.time_completed, 'unixepoch') as date_completed
            FROM articles a
            LEFT JOIN reading_progress rp ON a.id = rp.article_id
            WHERE a.success = 1
            ORDER BY a.time_added DESC
        ''')
        
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(columns)
            writer.writerows(rows)
            
        conn.close()
        
        print(f"Reading data exported to: {output_file}")
        
    def print_stats(self):
        """Print reading statistics."""
        stats = self.get_reading_stats()
        
        print("Reading Statistics")
        print("=" * 50)
        print(f"Total articles: {stats['total_articles']}")
        print(f"Total reading time: {stats['total_reading_time_hours']} hours")
        
        if stats['average_rating']:
            print(f"Average rating: {stats['average_rating']}/5")
            
        print("\n📈 Articles by Status:")
        for status, count in stats['by_status'].items():
            print(f"  {status}: {count}")
            
        if stats['top_tags']:
            print("\nTop Tags:")
            for tag, count in stats['top_tags'][:5]:
                print(f"  {tag}: {count}")


def main():
    import sys
    
    tracker = ReadingTracker()
    
    if len(sys.argv) < 2:
        print("Usage: python reading_tracker.py <command> [args]")
        print("Commands:")
        print("  stats                    - Show reading statistics")
        print("  list [status] [limit]    - List articles by status")
        print("  mark <url> <status>      - Mark article status")
        print("  export <file>            - Export reading data")
        print("  session <url> start      - Start reading session")
        print("  session <url> end        - End reading session")
        return
        
    command = sys.argv[1]
    
    if command == "stats":
        tracker.print_stats()
        
    elif command == "list":
        status = sys.argv[2] if len(sys.argv) > 2 else 'unread'
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 20
        
        articles = tracker.get_reading_list(status, limit)
        print(f"\n{status.title()} Articles ({len(articles)}):")
        print("-" * 50)
        
        for article in articles:
            print(f"- {article['title'][:60]}...")
            print(f"   URL: {article['url']}")
            print(f"   Time: {article['reading_time_estimate']} min")
            if article['tags']:
                print(f"   Tags: {article['tags']}")
            print()
            
    elif command == "mark" and len(sys.argv) >= 4:
        url = sys.argv[2]
        status = sys.argv[3]
        
        article = tracker.get_article_by_url(url)
        if article:
            tracker.update_reading_status(article['id'], status)
            print(f"✓ Marked '{article['title']}' as {status}")
        else:
            print(f"✗ Article not found: {url}")
            
    elif command == "export" and len(sys.argv) >= 3:
        output_file = sys.argv[2]
        tracker.export_reading_data(output_file)
        
    else:
        print("Invalid command or arguments")


if __name__ == "__main__":
    main()