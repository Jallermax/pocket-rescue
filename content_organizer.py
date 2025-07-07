#!/usr/bin/env python3
"""
Content organizer with folder structure and search capabilities.
Manages saved articles and provides search functionality.
"""

import os
import sqlite3
import json
import shutil
from pathlib import Path
from datetime import datetime
import re
import hashlib


class ContentOrganizer:
    def __init__(self, base_dir="saved_articles"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        self.db_path = self.base_dir / "articles.db"
        self.search_index_path = self.base_dir / "search_index.json"
        
    def create_folder_structure(self):
        """Create organized folder structure based on tags and categories."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT tags, file_path FROM articles WHERE success = 1 AND tags IS NOT NULL')
        articles = cursor.fetchall()
        conn.close()
        
        # Create category folders
        categories = {
            'programming': ['programming', 'coding', 'codding', 'development', 'python', 'javascript', 'tech'],
            'reading': ['_reading', '_practice', 'education', 'learning'],
            'productivity': ['productivity', 'gtd', 'time', 'management'],
            'security': ['security', 'hacking', 'privacy', 'cryptography'],
            'games': ['gamedev', 'games', 'gaming'],
            'career': ['career', 'job', 'work', 'interview'],
            'quick_reads': ['1 minute', '2 minutes', '5 minutes'],
            'long_reads': ['30+ minutes', '45 minutes', '1 hour'],
            'archived': ['archive']
        }
        
        # Create folders
        for category in categories:
            category_path = self.base_dir / category
            category_path.mkdir(exist_ok=True)
            
        # Organize articles
        moved_count = 0
        for tags, file_path in articles:
            if not file_path or not Path(file_path).exists():
                continue
                
            tags_lower = tags.lower()
            source_path = Path(file_path)
            
            # Determine category
            target_category = 'uncategorized'
            for category, keywords in categories.items():
                if any(keyword in tags_lower for keyword in keywords):
                    target_category = category
                    break
                    
            # Create target directory
            target_dir = self.base_dir / target_category
            target_dir.mkdir(exist_ok=True)
            
            # Move file if not already in correct location
            target_path = target_dir / source_path.name
            if source_path.parent != target_dir:
                try:
                    shutil.move(str(source_path), str(target_path))
                    
                    # Update database with new path
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    cursor.execute('UPDATE articles SET file_path = ? WHERE file_path = ?', 
                                 (str(target_path), str(source_path)))
                    conn.commit()
                    conn.close()
                    
                    moved_count += 1
                except Exception as e:
                    print(f"Error moving {source_path}: {e}")
                    
        print(f"Organized {moved_count} articles into category folders")
        
    def build_search_index(self):
        """Build search index from all articles."""
        print("Building search index...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, url, title, tags, file_path FROM articles WHERE success = 1')
        articles = cursor.fetchall()
        conn.close()
        
        search_index = {}
        
        for article_id, url, title, tags, file_path in articles:
            # Read article content
            content = ""
            if file_path and Path(file_path).exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
                    continue
                    
            # Extract text for indexing
            text_to_index = f"{title} {tags} {content}".lower()
            
            # Create word index
            words = re.findall(r'\b\w+\b', text_to_index)
            word_freq = {}
            for word in words:
                if len(word) >= 3:  # Skip very short words
                    word_freq[word] = word_freq.get(word, 0) + 1
                    
            search_index[article_id] = {
                'url': url,
                'title': title,
                'tags': tags,
                'file_path': file_path,
                'word_freq': word_freq,
                'content_length': len(content)
            }
            
        # Save index
        with open(self.search_index_path, 'w', encoding='utf-8') as f:
            json.dump(search_index, f, indent=2)
            
        print(f"Search index built with {len(search_index)} articles")
        
    def search_articles(self, query, limit=20):
        """Search articles using the search index."""
        if not self.search_index_path.exists():
            print("Search index not found. Building index...")
            self.build_search_index()
            
        with open(self.search_index_path, 'r', encoding='utf-8') as f:
            search_index = json.load(f)
            
        query_words = re.findall(r'\b\w+\b', query.lower())
        if not query_words:
            return []
            
        # Calculate relevance scores
        results = []
        for article_id, article_data in search_index.items():
            score = 0
            
            # Title matches (higher weight)
            title_lower = article_data['title'].lower()
            for word in query_words:
                if word in title_lower:
                    score += 10
                    
            # Tag matches (high weight)
            tags_lower = article_data.get('tags', '').lower()
            for word in query_words:
                if word in tags_lower:
                    score += 8
                    
            # Content matches
            word_freq = article_data.get('word_freq', {})
            for word in query_words:
                if word in word_freq:
                    score += word_freq[word]
                    
            # Partial matches
            for word in query_words:
                for indexed_word in word_freq:
                    if word in indexed_word or indexed_word in word:
                        score += 1
                        
            if score > 0:
                results.append({
                    'article_id': article_id,
                    'score': score,
                    'title': article_data['title'],
                    'url': article_data['url'],
                    'tags': article_data.get('tags', ''),
                    'file_path': article_data.get('file_path', '')
                })
                
        # Sort by relevance score
        results.sort(key=lambda x: x['score'], reverse=True)
        
        return results[:limit]
        
    def get_duplicate_articles(self):
        """Find potential duplicate articles based on title similarity."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, title, url FROM articles WHERE success = 1')
        articles = cursor.fetchall()
        conn.close()
        
        duplicates = []
        
        for i, (id1, title1, url1) in enumerate(articles):
            for id2, title2, url2 in articles[i+1:]:
                # Check title similarity
                title1_clean = re.sub(r'[^\w\s]', '', title1.lower())
                title2_clean = re.sub(r'[^\w\s]', '', title2.lower())
                
                # Simple similarity check
                words1 = set(title1_clean.split())
                words2 = set(title2_clean.split())
                
                if len(words1) > 0 and len(words2) > 0:
                    similarity = len(words1 & words2) / len(words1 | words2)
                    if similarity > 0.8:  # 80% similarity threshold
                        duplicates.append({
                            'id1': id1, 'title1': title1, 'url1': url1,
                            'id2': id2, 'title2': title2, 'url2': url2,
                            'similarity': similarity
                        })
                        
        return duplicates
        
    def clean_duplicate_articles(self, duplicates, keep_first=True):
        """Remove duplicate articles."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        removed_count = 0
        
        for dup in duplicates:
            # Decide which to keep
            keep_id = dup['id1'] if keep_first else dup['id2']
            remove_id = dup['id2'] if keep_first else dup['id1']
            
            # Get file path to delete
            cursor.execute('SELECT file_path FROM articles WHERE id = ?', (remove_id,))
            result = cursor.fetchone()
            
            if result and result[0]:
                file_path = Path(result[0])
                if file_path.exists():
                    try:
                        file_path.unlink()
                    except Exception as e:
                        print(f"Error deleting {file_path}: {e}")
                        
            # Remove from database
            cursor.execute('DELETE FROM articles WHERE id = ?', (remove_id,))
            removed_count += 1
            
        conn.commit()
        conn.close()
        
        print(f"Removed {removed_count} duplicate articles")
        
    def get_statistics(self):
        """Get content organization statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total articles
        cursor.execute('SELECT COUNT(*) FROM articles WHERE success = 1')
        total_articles = cursor.fetchone()[0]
        
        # Articles by category (based on folder structure)
        categories = {}
        for category_dir in self.base_dir.iterdir():
            if category_dir.is_dir() and category_dir.name != '__pycache__':
                file_count = len(list(category_dir.glob('*.md')))
                if file_count > 0:
                    categories[category_dir.name] = file_count
                    
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
        
        # File sizes
        cursor.execute('SELECT SUM(content_length) FROM articles WHERE success = 1')
        total_content_size = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            'total_articles': total_articles,
            'categories': categories,
            'top_tags': top_tags,
            'total_content_size': total_content_size,
            'avg_content_size': total_content_size // total_articles if total_articles > 0 else 0
        }
        
    def print_statistics(self):
        """Print organization statistics."""
        stats = self.get_statistics()
        
        print("\nContent Organization Statistics")
        print("=" * 50)
        print(f"Total articles: {stats['total_articles']}")
        print(f"Total content size: {stats['total_content_size']:,} characters")
        print(f"Average article size: {stats['avg_content_size']:,} characters")
        
        print("\nArticles by Category:")
        for category, count in sorted(stats['categories'].items()):
            print(f"  {category}: {count}")
            
        if stats['top_tags']:
            print("\nTop Tags:")
            for tag, count in stats['top_tags'][:5]:
                print(f"  {tag}: {count}")


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python content_organizer.py <command> [args]")
        print("Commands:")
        print("  organize           - Organize articles into category folders")
        print("  index              - Build search index")
        print("  search <query>     - Search articles")
        print("  duplicates         - Find duplicate articles")
        print("  clean-duplicates   - Remove duplicate articles")
        print("  stats              - Show organization statistics")
        return
        
    command = sys.argv[1]
    organizer = ContentOrganizer()
    
    if command == "organize":
        organizer.create_folder_structure()
        
    elif command == "index":
        organizer.build_search_index()
        
    elif command == "search" and len(sys.argv) >= 3:
        query = ' '.join(sys.argv[2:])
        results = organizer.search_articles(query)
        
        print(f"\n🔍 Search Results for '{query}' ({len(results)} found):")
        print("-" * 50)
        
        for i, result in enumerate(results, 1):
            print(f"{i:2d}. {result['title'][:60]}...")
            print(f"     Score: {result['score']}, Tags: {result['tags'][:40]}...")
            print(f"     URL: {result['url']}")
            print()
            
    elif command == "duplicates":
        duplicates = organizer.get_duplicate_articles()
        
        print(f"\n🔍 Found {len(duplicates)} potential duplicates:")
        print("-" * 50)
        
        for i, dup in enumerate(duplicates, 1):
            print(f"{i:2d}. Similarity: {dup['similarity']:.2f}")
            print(f"     A: {dup['title1'][:50]}...")
            print(f"     B: {dup['title2'][:50]}...")
            print()
            
    elif command == "clean-duplicates":
        duplicates = organizer.get_duplicate_articles()
        if duplicates:
            print(f"Found {len(duplicates)} duplicates. Removing...")
            organizer.clean_duplicate_articles(duplicates)
        else:
            print("No duplicates found.")
            
    elif command == "stats":
        organizer.print_statistics()
        
    else:
        print("Invalid command")


if __name__ == "__main__":
    main()