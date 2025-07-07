#!/usr/bin/env python3
"""
Database utilities for Pocket Rescue.
Shared SQLite database helpers and utilities.
"""

import sqlite3
from pathlib import Path
from datetime import datetime


class DatabaseManager:
    """Manages SQLite database operations for Pocket Rescue."""
    
    def __init__(self, db_path="saved_articles/articles.db"):
        """Initialize database manager."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        
    def get_connection(self):
        """Get database connection."""
        return sqlite3.connect(self.db_path)
        
    def init_database(self):
        """Initialize or upgrade database schema."""
        conn = self.get_connection()
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
                success BOOLEAN DEFAULT 0,
                created_at INTEGER DEFAULT (strftime('%s', 'now')),
                updated_at INTEGER DEFAULT (strftime('%s', 'now'))
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
                created_at INTEGER DEFAULT (strftime('%s', 'now')),
                updated_at INTEGER DEFAULT (strftime('%s', 'now')),
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
                created_at INTEGER DEFAULT (strftime('%s', 'now')),
                FOREIGN KEY (article_id) REFERENCES articles (id)
            )
        ''')
        
        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_url ON articles(url)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_status ON articles(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_success ON articles(success)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_reading_progress_article_id ON reading_progress(article_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_reading_sessions_article_id ON reading_sessions(article_id)')
        
        conn.commit()
        conn.close()
        
    def insert_article(self, url, title=None, tags=None, status='unread', time_added=None):
        """Insert a new article into the database."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        current_time = int(datetime.now().timestamp())
        time_added = time_added or current_time
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO articles 
                (url, title, tags, status, time_added, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (url, title, tags, status, time_added, current_time))
            
            article_id = cursor.lastrowid
            conn.commit()
            return article_id
            
        except sqlite3.Error as e:
            conn.rollback()
            raise Exception(f"Database error inserting article: {e}")
        finally:
            conn.close()
            
    def update_article_content(self, url, file_path=None, content_length=None, 
                             scrape_method=None, success=False, archive_url=None):
        """Update article content information."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        current_time = int(datetime.now().timestamp())
        
        try:
            cursor.execute('''
                UPDATE articles 
                SET file_path = ?, content_length = ?, scrape_method = ?, 
                    success = ?, archive_url = ?, time_scraped = ?, updated_at = ?
                WHERE url = ?
            ''', (file_path, content_length, scrape_method, success, 
                  archive_url, current_time, current_time, url))
            
            conn.commit()
            return cursor.rowcount > 0
            
        except sqlite3.Error as e:
            conn.rollback()
            raise Exception(f"Database error updating article content: {e}")
        finally:
            conn.close()
            
    def get_article_by_url(self, url):
        """Get article by URL."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM articles WHERE url = ?', (url,))
            row = cursor.fetchone()
            
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            return None
            
        except sqlite3.Error as e:
            raise Exception(f"Database error getting article: {e}")
        finally:
            conn.close()
            
    def get_articles_by_criteria(self, status=None, success=None, limit=None, offset=0):
        """Get articles by various criteria."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM articles WHERE 1=1"
        params = []
        
        if status is not None:
            query += " AND status = ?"
            params.append(status)
            
        if success is not None:
            query += " AND success = ?"
            params.append(success)
            
        query += " ORDER BY time_added DESC"
        
        if limit:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
        try:
            cursor.execute(query, params)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            
            return [dict(zip(columns, row)) for row in rows]
            
        except sqlite3.Error as e:
            raise Exception(f"Database error querying articles: {e}")
        finally:
            conn.close()
            
    def get_statistics(self):
        """Get database statistics."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            stats = {}
            
            # Total articles
            cursor.execute('SELECT COUNT(*) FROM articles')
            stats['total_articles'] = cursor.fetchone()[0]
            
            # Successful articles
            cursor.execute('SELECT COUNT(*) FROM articles WHERE success = 1')
            stats['successful_articles'] = cursor.fetchone()[0]
            
            # Articles by status
            cursor.execute('''
                SELECT status, COUNT(*) 
                FROM articles 
                GROUP BY status
            ''')
            stats['by_status'] = dict(cursor.fetchall())
            
            # Articles by scrape method
            cursor.execute('''
                SELECT scrape_method, COUNT(*) 
                FROM articles 
                WHERE success = 1 AND scrape_method IS NOT NULL
                GROUP BY scrape_method
            ''')
            stats['by_scrape_method'] = dict(cursor.fetchall())
            
            # Reading progress
            cursor.execute('''
                SELECT reading_status, COUNT(*) 
                FROM reading_progress 
                GROUP BY reading_status
            ''')
            stats['reading_progress'] = dict(cursor.fetchall())
            
            return stats
            
        except sqlite3.Error as e:
            raise Exception(f"Database error getting statistics: {e}")
        finally:
            conn.close()
            
    def cleanup_database(self, remove_failed=False):
        """Clean up database by removing orphaned records."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Remove reading progress for non-existent articles
            cursor.execute('''
                DELETE FROM reading_progress 
                WHERE article_id NOT IN (SELECT id FROM articles)
            ''')
            progress_cleaned = cursor.rowcount
            
            # Remove reading sessions for non-existent articles  
            cursor.execute('''
                DELETE FROM reading_sessions 
                WHERE article_id NOT IN (SELECT id FROM articles)
            ''')
            sessions_cleaned = cursor.rowcount
            
            # Optionally remove failed articles
            if remove_failed:
                cursor.execute('DELETE FROM articles WHERE success = 0')
                failed_removed = cursor.rowcount
            else:
                failed_removed = 0
                
            conn.commit()
            
            return {
                'progress_cleaned': progress_cleaned,
                'sessions_cleaned': sessions_cleaned,
                'failed_removed': failed_removed
            }
            
        except sqlite3.Error as e:
            conn.rollback()
            raise Exception(f"Database error during cleanup: {e}")
        finally:
            conn.close()
            
    def export_to_csv(self, output_file, include_content=False):
        """Export database to CSV."""
        import csv
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if include_content:
                query = '''
                    SELECT 
                        a.url, a.title, a.tags, a.status, a.time_added,
                        a.file_path, a.content_length, a.scrape_method, a.success,
                        COALESCE(rp.reading_status, 'unread') as reading_status,
                        rp.progress_percent, rp.rating
                    FROM articles a
                    LEFT JOIN reading_progress rp ON a.id = rp.article_id
                    ORDER BY a.time_added DESC
                '''
            else:
                query = '''
                    SELECT url, title, tags, status, time_added
                    FROM articles
                    ORDER BY time_added DESC
                '''
                
            cursor.execute(query)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(columns)
                writer.writerows(rows)
                
            return len(rows)
            
        except (sqlite3.Error, IOError) as e:
            raise Exception(f"Error exporting to CSV: {e}")
        finally:
            conn.close()


def main():
    """Test database functionality."""
    import sys
    
    db = DatabaseManager()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "init":
            print("Initializing database...")
            db.init_database()
            print("✓ Database initialized")
            
        elif command == "stats":
            stats = db.get_statistics()
            print("Database Statistics:")
            print("=" * 30)
            for key, value in stats.items():
                if isinstance(value, dict):
                    print(f"{key}:")
                    for k, v in value.items():
                        print(f"  {k}: {v}")
                else:
                    print(f"{key}: {value}")
                    
        elif command == "cleanup":
            result = db.cleanup_database()
            print(f"Cleanup completed:")
            print(f"  Progress records cleaned: {result['progress_cleaned']}")
            print(f"  Session records cleaned: {result['sessions_cleaned']}")
            
        elif command == "export" and len(sys.argv) > 2:
            output_file = sys.argv[2]
            count = db.export_to_csv(output_file)
            print(f"✓ Exported {count} records to {output_file}")
            
        else:
            print("Usage: python database.py <command>")
            print("Commands: init, stats, cleanup, export <file>")
    else:
        print("Testing database...")
        db.init_database()
        stats = db.get_statistics()
        print(f"Database ready. Total articles: {stats['total_articles']}")


if __name__ == "__main__":
    main()