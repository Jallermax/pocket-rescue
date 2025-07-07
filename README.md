# Pocket Rescue 🆘

A comprehensive toolkit for preserving your Pocket articles before the service shuts down. This suite of Python scripts helps you download, organize, and manage your saved articles locally.

## 🚨 Urgent: Pocket Shutdown Timeline

- **May 22, 2025**: Pocket removed from app stores
- **July 8, 2025**: Pocket officially shuts down
- **October 8, 2025**: All user data permanently deleted

**You have until October 8, 2025 to export your data!**

## 📋 What This Does

- ✅ Checks link validity (skips archived articles by default)
- 📥 Downloads full article content (text extraction)
- 🕰️ Recovers dead links from Wayback Machine
- 📁 Organizes articles into categorized folders
- 🎯 Prioritizes articles based on tags and reading time
- 📊 Tracks reading progress and statistics
- 🔍 Provides full-text search capabilities

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
```

### 2. Export your data from Pocket in csv

```bash
# Export your Pocket data as CSV
# Go to https://getpocket.com/export
# Download the CSV file and place it in the project directory
# Rename the file to 'part_000000.csv' for consistency
# Alternatively, you can use the Pocket API to export your data
https://getpocket.com/developer/docs/authentication
```
Additionally, edit priority_filter.py to use your labels and priority weights.

### 3. Run Full Rescue

```bash
# Complete rescue workflow (recommended)
python pocket_rescue.py full-rescue

# Quick rescue (high-priority articles only)
python pocket_rescue.py quick-rescue
```

### 4. Create Reading Plan

```bash
# Generate personalized reading plan
python pocket_rescue.py reading-plan --daily-minutes 30
```

## 📁 Output Structure

```
saved_articles/
├── programming/          # Programming & coding articles
├── reading/             # Articles tagged for reading
├── productivity/        # Productivity & time management
├── security/           # Security & privacy articles
├── quick_reads/        # Short articles (1-5 minutes)
├── long_reads/         # Long articles (30+ minutes)
├── wayback_archived/   # Recovered from Wayback Machine
├── articles.db         # SQLite database with metadata
└── search_index.json   # Search index for fast lookup
```

## 🔧 Individual Scripts

### Link Checker
```bash
# Check all links (skips archived by default)
python check_links.py

# Include archived articles
python check_links.py --include-archived
```

### Content Scraper
```bash
# Scrape article content
python content_scraper.py

# Use more workers for faster processing
python content_scraper.py --workers 20
```

### Wayback Machine Recovery
```bash
# Recover content from invalid links
python wayback_scraper.py invalid_links.csv
```

### Priority Analysis
```bash
# Analyze article priorities
python priority_filter.py analyze part_000000.csv

# Filter high-priority articles
python priority_filter.py filter part_000000.csv --priority high,critical --status unread
```

### Reading Tracker
```bash
# Show reading statistics
python reading_tracker.py stats

# List unread articles
python reading_tracker.py list unread 20

# Mark article as read
python reading_tracker.py mark "https://example.com/article" completed
```

### Content Organizer
```bash
# Organize into folders
python content_organizer.py organize

# Build search index
python content_organizer.py index

# Search articles
python content_organizer.py search "python programming"

# Show statistics
python content_organizer.py stats
```

## 🎯 Priority System

Articles are automatically prioritized based on:

### High Priority (50+ points)
- Tagged with `_reading` or `_practice`
- Programming/coding content
- Short reading time (1-5 minutes)
- Recent additions

### Medium Priority (10-25 points)
- Educational content
- Productivity articles
- Medium reading time (10-30 minutes)

### Low Priority (5-10 points)
- Long articles (30+ minutes)
- Gaming content
- Older articles

### Minimal Priority (<5 points)
- Archived articles
- No specific tags
- Very old content

## 🔍 Search Features

The search system indexes:
- Article titles (highest weight)
- Tags (high weight)
- Full article content
- Partial word matches

Search examples:
```bash
python content_organizer.py search "python programming"
python content_organizer.py search "productivity tips"
python content_organizer.py search "javascript tutorial"
```

## 📊 Statistics & Analytics

Track your reading progress:
- Total articles saved
- Reading time estimates
- Articles by category
- Completion rates
- Most popular tags

## 🚀 Performance Tips

1. **Use more workers**: `--workers 20` for faster scraping
2. **Skip archived articles**: Default behavior to focus on unread content
3. **Quick rescue mode**: Process only high-priority articles first
4. **Batch operations**: Use the master script for coordinated workflows

## 🛠️ Troubleshooting

### Common Issues

**Script fails with import errors**
```bash
# Make sure virtual environment is activated
source .venv/bin/activate
uv pip install -r requirements.txt
```

**Too many failed links**
```bash
# Try Wayback Machine recovery
python wayback_scraper.py invalid_links.csv
```

**Search not working**
```bash
# Rebuild search index
python content_organizer.py index
```

### Rate Limiting
- Scripts include delays to be respectful to websites
- Wayback Machine requests are spaced 2 seconds apart
- Adjust `max_workers` if you encounter rate limits

## 📝 Migration Options

After saving your articles, you can:

1. **Keep local**: Use the built-in reading tracker and search
2. **Import to Notion**: Export CSV and import to Notion
3. **Use Wallabag**: Self-hosted read-later service
4. **Export to Obsidian**: Convert markdown files to Obsidian vault

## 🤝 Contributing

Found a bug or want to add features? Feel free to:
- Report issues
- Submit pull requests
- Share your improvements

## ⚖️ Legal & Ethical Use

- Respect robots.txt and website terms of service
- Don't overload servers with requests
- Use saved content for personal reading only
- Consider supporting original authors

## 🎉 Success Stories

After running Pocket Rescue, you'll have:
- ✅ All your articles safely preserved locally
- 📁 Organized folder structure for easy browsing
- 🔍 Full-text search of your entire collection
- 📊 Reading analytics and progress tracking
- 🎯 Prioritized reading list based on your interests

**Don't lose your reading list! Run Pocket Rescue today!**