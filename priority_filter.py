#!/usr/bin/env python3
"""
Priority filtering system for Pocket articles.
Filters and prioritizes articles based on tags, reading time, and status.
"""

import csv
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3


class PriorityFilter:
    def __init__(self, base_dir="saved_articles"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        
        # Priority rules (higher score = higher priority)
        self.priority_rules = {
            'reading_tags': {
                '_reading': 50,
                '_practice': 40,
                'education': 30,
                'learning': 25
            },
            'time_categories': {
                '1 minute or less': 15,
                '2 minutes or less': 15,
                '5 minutes or less': 10,
                '10 minutes or less': 8,
                '15 minutes or less': 6,
                '30 minutes or less': 4,
                '30+ minutes': 2
            },
            'topic_priorities': {
                'programming': 20,
                'coding': 20,
                'codding': 20,  # Common misspelling
                'development': 15,
                'tech': 15,
                'productivity': 10,
                'security': 12,
                'gamedev': 8,
                'python': 18,
                'javascript': 15,
                'career': 12
            },
            'status_multipliers': {
                'unread': 1.0,
                'archive': 0.1  # Much lower priority for archived
            }
        }
        
    def calculate_priority_score(self, row):
        """Calculate priority score for an article."""
        score = 0
        
        # Base score
        score += 1
        
        # Reading tags
        tags = row.get('tags', '').lower()
        for tag, points in self.priority_rules['reading_tags'].items():
            if tag in tags:
                score += points
                
        # Time estimates
        for time_cat, points in self.priority_rules['time_categories'].items():
            if time_cat in tags:
                score += points
                break
                
        # Topic priorities
        for topic, points in self.priority_rules['topic_priorities'].items():
            if topic in tags:
                score += points
                
        # Status multiplier
        status = row.get('status', 'unread').lower()
        multiplier = self.priority_rules['status_multipliers'].get(status, 1.0)
        score *= multiplier
        
        # Recency bonus (newer articles get slight boost)
        time_added = int(row.get('time_added', 0))
        if time_added > 0:
            days_old = (datetime.now().timestamp() - time_added) / 86400
            if days_old < 30:  # Articles less than 30 days old
                score += max(0, 10 - (days_old / 3))
                
        return round(score, 2)
        
    def categorize_priority(self, score):
        """Categorize priority based on score."""
        if score >= 50:
            return 'critical'
        elif score >= 25:
            return 'high'
        elif score >= 10:
            return 'medium'
        elif score >= 5:
            return 'low'
        else:
            return 'minimal'
            
    def analyze_csv(self, csv_file):
        """Analyze CSV and assign priorities."""
        print(f"Analyzing priorities for: {csv_file}")
        
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            rows = list(reader)
            
        prioritized_articles = []
        
        for row in rows:
            score = self.calculate_priority_score(row)
            priority = self.categorize_priority(score)
            
            article = {
                'url': row['url'],
                'title': row['title'],
                'tags': row.get('tags', ''),
                'status': row.get('status', 'unread'),
                'time_added': int(row.get('time_added', 0)),
                'priority_score': score,
                'priority_category': priority
            }
            
            prioritized_articles.append(article)
            
        # Sort by priority score (descending)
        prioritized_articles.sort(key=lambda x: x['priority_score'], reverse=True)
        
        return prioritized_articles
        
    def filter_by_criteria(self, articles, criteria):
        """Filter articles by various criteria."""
        filtered = articles.copy()
        
        # Priority level filter
        if criteria.get('priority'):
            priorities = criteria['priority'] if isinstance(criteria['priority'], list) else [criteria['priority']]
            filtered = [a for a in filtered if a['priority_category'] in priorities]
            
        # Status filter
        if criteria.get('status'):
            statuses = criteria['status'] if isinstance(criteria['status'], list) else [criteria['status']]
            filtered = [a for a in filtered if a['status'] in statuses]
            
        # Tag filter
        if criteria.get('tags'):
            tag_filters = criteria['tags'] if isinstance(criteria['tags'], list) else [criteria['tags']]
            filtered = [a for a in filtered if any(tag.lower() in a['tags'].lower() for tag in tag_filters)]
            
        # Time range filter
        if criteria.get('days_old'):
            cutoff_time = datetime.now().timestamp() - (criteria['days_old'] * 86400)
            filtered = [a for a in filtered if a['time_added'] >= cutoff_time]
            
        # Limit results
        if criteria.get('limit'):
            filtered = filtered[:criteria['limit']]
            
        return filtered
        
    def create_reading_plan(self, articles, daily_reading_time=30):
        """Create a reading plan based on available time."""
        plan = {
            'daily_reading_time': daily_reading_time,
            'plans': []
        }
        
        # Group articles by estimated reading time
        quick_reads = []  # <= 5 minutes
        medium_reads = []  # 5-15 minutes
        long_reads = []  # > 15 minutes
        
        for article in articles:
            tags = article['tags'].lower()
            
            if any(t in tags for t in ['1 minute', '2 minutes', '5 minutes']):
                reading_time = 5
                quick_reads.append({**article, 'estimated_time': reading_time})
            elif any(t in tags for t in ['10 minutes', '15 minutes']):
                reading_time = 12
                medium_reads.append({**article, 'estimated_time': reading_time})
            elif '30 minutes' in tags:
                reading_time = 30
                long_reads.append({**article, 'estimated_time': reading_time})
            else:
                reading_time = 10  # Default
                medium_reads.append({**article, 'estimated_time': reading_time})
        
        # Create daily plans
        day = 1
        while quick_reads or medium_reads or long_reads:
            daily_plan = {
                'day': day,
                'articles': [],
                'total_time': 0
            }
            
            remaining_time = daily_reading_time
            
            # Try to fit articles into the day
            for article_list in [quick_reads, medium_reads, long_reads]:
                i = 0
                while i < len(article_list) and remaining_time > 0:
                    article = article_list[i]
                    if article['estimated_time'] <= remaining_time:
                        daily_plan['articles'].append(article_list.pop(i))
                        daily_plan['total_time'] += article['estimated_time']
                        remaining_time -= article['estimated_time']
                    else:
                        i += 1
                        
            if daily_plan['articles']:
                plan['plans'].append(daily_plan)
                day += 1
            else:
                # No more articles can fit
                break
                
        return plan
        
    def export_priority_list(self, articles, output_file):
        """Export prioritized articles to CSV."""
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['priority_category', 'priority_score', 'title', 'url', 'tags', 'status', 'date_added']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for article in articles:
                writer.writerow({
                    'priority_category': article['priority_category'],
                    'priority_score': article['priority_score'],
                    'title': article['title'],
                    'url': article['url'],
                    'tags': article['tags'],
                    'status': article['status'],
                    'date_added': datetime.fromtimestamp(article['time_added']).strftime('%Y-%m-%d') if article['time_added'] > 0 else ''
                })
                
        print(f"Priority list exported to: {output_file}")
        
    def print_priority_summary(self, articles):
        """Print priority summary."""
        priority_counts = {}
        for article in articles:
            priority = article['priority_category']
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
            
        print("\nPriority Summary")
        print("=" * 50)
        
        for priority in ['critical', 'high', 'medium', 'low', 'minimal']:
            count = priority_counts.get(priority, 0)
            if count > 0:
                print(f"{priority.capitalize()}: {count} articles")
                
        print(f"\nTotal articles: {len(articles)}")
        
        # Show top 10 highest priority articles
        print("\nTop 10 Highest Priority Articles:")
        print("-" * 50)
        
        for i, article in enumerate(articles[:10], 1):
            print(f"{i:2d}. [{article['priority_category'].upper()}] {article['title'][:50]}...")
            print(f"     Score: {article['priority_score']}, Tags: {article['tags'][:40]}...")
            print()


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python priority_filter.py <command> [args]")
        print("Commands:")
        print("  analyze <csv_file>                    - Analyze and prioritize articles")
        print("  filter <csv_file> [criteria]          - Filter articles by criteria")
        print("  plan <csv_file> [daily_time]          - Create reading plan")
        print("  export <csv_file> <output_file>       - Export prioritized list")
        print("\nFilter criteria examples:")
        print("  --priority high,critical")
        print("  --status unread")
        print("  --tags programming,coding")
        print("  --days-old 90")
        print("  --limit 50")
        return
        
    command = sys.argv[1]
    
    if command == "analyze" and len(sys.argv) >= 3:
        csv_file = sys.argv[2]
        filter_obj = PriorityFilter()
        articles = filter_obj.analyze_csv(csv_file)
        filter_obj.print_priority_summary(articles)
        
    elif command == "filter" and len(sys.argv) >= 3:
        csv_file = sys.argv[2]
        filter_obj = PriorityFilter()
        articles = filter_obj.analyze_csv(csv_file)
        
        # Parse criteria from command line
        criteria = {}
        i = 3
        while i < len(sys.argv):
            if sys.argv[i] == "--priority" and i + 1 < len(sys.argv):
                criteria['priority'] = sys.argv[i + 1].split(',')
                i += 2
            elif sys.argv[i] == "--status" and i + 1 < len(sys.argv):
                criteria['status'] = sys.argv[i + 1].split(',')
                i += 2
            elif sys.argv[i] == "--tags" and i + 1 < len(sys.argv):
                criteria['tags'] = sys.argv[i + 1].split(',')
                i += 2
            elif sys.argv[i] == "--days-old" and i + 1 < len(sys.argv):
                criteria['days_old'] = int(sys.argv[i + 1])
                i += 2
            elif sys.argv[i] == "--limit" and i + 1 < len(sys.argv):
                criteria['limit'] = int(sys.argv[i + 1])
                i += 2
            else:
                i += 1
                
        filtered_articles = filter_obj.filter_by_criteria(articles, criteria)
        filter_obj.print_priority_summary(filtered_articles)
        
    elif command == "plan" and len(sys.argv) >= 3:
        csv_file = sys.argv[2]
        daily_time = int(sys.argv[3]) if len(sys.argv) > 3 else 30
        
        filter_obj = PriorityFilter()
        articles = filter_obj.analyze_csv(csv_file)
        
        # Filter to only unread articles
        unread_articles = [a for a in articles if a['status'] == 'unread']
        
        plan = filter_obj.create_reading_plan(unread_articles, daily_time)
        
        print(f"\n📅 Reading Plan ({daily_time} minutes/day)")
        print("=" * 50)
        
        for day_plan in plan['plans']:
            print(f"\nDay {day_plan['day']} ({day_plan['total_time']} minutes):")
            for article in day_plan['articles']:
                print(f"  • {article['title'][:50]}... ({article['estimated_time']} min)")
                
        total_days = len(plan['plans'])
        total_articles = sum(len(day['articles']) for day in plan['plans'])
        print(f"\nTotal: {total_articles} articles over {total_days} days")
        
    elif command == "export" and len(sys.argv) >= 4:
        csv_file = sys.argv[2]
        output_file = sys.argv[3]
        
        filter_obj = PriorityFilter()
        articles = filter_obj.analyze_csv(csv_file)
        filter_obj.export_priority_list(articles, output_file)
        
    else:
        print("Invalid command or missing arguments")


if __name__ == "__main__":
    main()