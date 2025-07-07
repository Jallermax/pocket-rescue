#!/usr/bin/env python3
"""
Pocket API data processor.
Processes API response data and exports to CSV format compatible with existing workflow.
"""

import csv
import json
from datetime import datetime
from pathlib import Path


class PocketProcessor:
    def __init__(self):
        """Initialize Pocket data processor."""
        # Column mapping configuration for Pocket articles
        self.column_mapping = {
            # Basic article information
            "item_id": True,
            "resolved_id": False,
            "given_url": True,
            "given_title": True,
            "resolved_title": True,
            "resolved_url": True,
            "excerpt": True,

            # Status and metadata
            "favorite": True,
            "status": True,
            "is_article": True,
            "is_index": False,
            "has_video": False,
            "has_image": False,

            # Time-related fields
            "time_added": True,
            "time_updated": True,
            "time_read": True,
            "time_favorited": True,

            # Content metrics
            "word_count": True,
            "time_to_read": True,
            "listen_duration_estimate": True,
            "lang": True,

            # Media and images
            "top_image_url": False,
            "images": False,
            "image": False,

            # Domain information
            "domain_metadata": False,

            # Additional metadata
            "sort_id": False,
            "tags": True
        }
        
    def filter_article_data(self, article):
        """Filter article data based on column mapping configuration."""
        return {k: v for k, v in article.items() if self.column_mapping.get(k, False)}

    def process_articles(self, articles_response):
        """Process all articles and return filtered data."""
        if not isinstance(articles_response, dict) or 'list' not in articles_response:
            raise ValueError("Invalid articles response format")
            
        articles = articles_response['list']
        filtered_articles = {}
        
        for item_id, item in articles.items():
            filtered_articles[item_id] = self.filter_article_data(item)
            
        return filtered_articles

    def convert_timestamp(self, timestamp):
        """Convert Unix timestamp to readable datetime."""
        if timestamp and timestamp != "0" and str(timestamp) != "0":
            try:
                return datetime.fromtimestamp(int(timestamp)).strftime('%Y-%m-%d %H:%M:%S')
            except (ValueError, OSError):
                return ""
        return ""

    def format_tags(self, tags):
        """Format tags dictionary as a comma-separated string."""
        if tags and isinstance(tags, dict):
            return ", ".join(tags.keys())
        elif tags and isinstance(tags, str):
            return tags
        return ""

    def format_status(self, status):
        """Convert Pocket status to readable format."""
        status_map = {
            "0": "unread",
            "1": "archive", 
            "2": "deleted"
        }
        return status_map.get(str(status), "unread")

    def prepare_csv_data(self, articles):
        """Prepare articles data for CSV export compatible with existing workflow."""
        csv_data = []
        
        for article in articles.values():
            # Create a copy for modification
            row = {}
            
            # Map to CSV column names expected by existing scripts
            row['url'] = article.get('resolved_url') or article.get('given_url', '')
            row['title'] = article.get('resolved_title') or article.get('given_title', '')
            row['tags'] = self.format_tags(article.get('tags'))
            row['status'] = self.format_status(article.get('status', '0'))
            row['time_added'] = article.get('time_added', '')
            
            # Additional useful fields
            row['excerpt'] = article.get('excerpt', '')
            row['word_count'] = article.get('word_count', '')
            row['time_to_read'] = article.get('time_to_read', '')
            row['favorite'] = "1" if str(article.get('favorite', '0')) == "1" else "0"
            row['lang'] = article.get('lang', '')
            
            # Convert timestamps
            row['time_added'] = self.convert_timestamp(row['time_added'])
            if article.get('time_updated'):
                row['time_updated'] = self.convert_timestamp(article.get('time_updated'))
            if article.get('time_read'):
                row['time_read'] = self.convert_timestamp(article.get('time_read'))
                
            csv_data.append(row)
            
        return csv_data

    def save_to_csv(self, articles, filename=None):
        """Save articles to CSV file compatible with existing pocket_rescue workflow."""
        if not filename:
            filename = f"part_000000.csv"  # Default name expected by existing scripts

        if not articles:
            print("No articles to save")
            return None

        # Prepare data for CSV
        csv_data = self.prepare_csv_data(articles)
        
        if not csv_data:
            print("No valid articles to save")
            return None

        # Get fieldnames from first row
        fieldnames = list(csv_data[0].keys())

        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(csv_data)

            print(f"✓ Saved {len(csv_data)} articles to {filename}")
            print(f"✓ CSV file is ready for pocket_rescue.py workflow")
            return filename
            
        except Exception as e:
            print(f"✗ Error saving CSV: {e}")
            return None

    def save_raw_json(self, articles_response, filename=None):
        """Save raw API response to JSON file for debugging/backup."""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"pocket_raw_{timestamp}.json"

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(articles_response, f, indent=2, ensure_ascii=False)
            print(f"✓ Raw API response saved to {filename}")
            return filename
        except Exception as e:
            print(f"✗ Error saving raw JSON: {e}")
            return None

    def get_statistics(self, articles):
        """Get statistics about the articles."""
        if not articles:
            return {}
            
        stats = {
            'total_articles': len(articles),
            'by_status': {},
            'by_favorite': {'yes': 0, 'no': 0},
            'with_tags': 0,
            'avg_word_count': 0,
            'languages': {}
        }
        
        total_words = 0
        word_count_articles = 0
        
        for article in articles.values():
            # Status counts
            status = self.format_status(article.get('status', '0'))
            stats['by_status'][status] = stats['by_status'].get(status, 0) + 1
            
            # Favorite counts
            is_favorite = str(article.get('favorite', '0')) == "1"
            stats['by_favorite']['yes' if is_favorite else 'no'] += 1
            
            # Tag counts
            if article.get('tags'):
                stats['with_tags'] += 1
                
            # Word count average
            word_count = article.get('word_count')
            if word_count and str(word_count).isdigit():
                total_words += int(word_count)
                word_count_articles += 1
                
            # Language counts
            lang = article.get('lang', 'unknown')
            stats['languages'][lang] = stats['languages'].get(lang, 0) + 1
            
        if word_count_articles > 0:
            stats['avg_word_count'] = round(total_words / word_count_articles)
            
        return stats
        
    def print_statistics(self, articles):
        """Print article statistics."""
        stats = self.get_statistics(articles)
        
        print("\nPocket Articles Statistics")
        print("=" * 50)
        
        # Handle empty statistics
        if not stats:
            print("No articles found")
            return
            
        print(f"Total articles: {stats['total_articles']}")
        
        if stats['by_status']:
            print(f"\nBy status:")
            for status, count in stats['by_status'].items():
                print(f"  {status}: {count}")
            
        print(f"\nFavorited: {stats['by_favorite']['yes']}")
        print(f"With tags: {stats['with_tags']}")
        
        if stats['avg_word_count'] > 0:
            print(f"Average word count: {stats['avg_word_count']}")
            
        if stats['languages']:
            print(f"\nTop languages:")
            sorted_langs = sorted(stats['languages'].items(), key=lambda x: x[1], reverse=True)
            for lang, count in sorted_langs[:5]:
                print(f"  {lang}: {count}")


def main():
    """Test processor functionality."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python processor.py <json_file>")
        print("Test the processor with a JSON file from the API")
        return
        
    json_file = sys.argv[1]
    processor = PocketProcessor()
    
    try:
        # Load test data
        with open(json_file, 'r', encoding='utf-8') as f:
            articles_response = json.load(f)
            
        print(f"Processing articles from {json_file}...")
        
        # Process articles
        filtered_articles = processor.process_articles(articles_response)
        
        # Show statistics
        processor.print_statistics(filtered_articles)
        
        # Save to CSV
        csv_file = processor.save_to_csv(filtered_articles)
        
        if csv_file:
            print(f"\n✓ Processing completed successfully!")
            print(f"✓ Ready to use with: python pocket_rescue.py full-rescue")
        
    except Exception as e:
        print(f"Processing failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()