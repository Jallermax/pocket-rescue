# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Environment Setup

Use `uv` as the package manager for this project:

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
```

## Core Commands for Development

### API-First Workflow (Recommended)
- `python pocket_rescue.py fetch-from-api` - Fetch articles directly from Pocket API
- `python pocket_rescue.py full-rescue` - Complete rescue workflow after API fetch
- `python pocket_rescue.py quick-rescue` - High-priority articles only (faster)

### Traditional CSV Workflow
- `python pocket_rescue.py full-rescue` - Complete rescue workflow (using existing CSV)
- `python pocket_rescue.py reading-plan --daily-minutes 30` - Generate reading plan
- `python pocket_rescue.py search "query"` - Search saved content

### Individual Module Commands (New Package Structure)
- `python -m pocket_rescue.core.link_checker` - Check URL validity
- `python -m pocket_rescue.core.content_scraper --workers 20` - Scrape content
- `python -m pocket_rescue.core.wayback_scraper invalid_links.csv` - Wayback recovery
- `python -m pocket_rescue.core.priority_filter analyze part_000000.csv` - Priority analysis
- `python -m pocket_rescue.core.content_organizer organize` - Organize into folders
- `python -m pocket_rescue.core.reading_tracker stats` - Reading statistics

### API Module Commands
- `python -m pocket_rescue.api.auth` - Test Pocket authentication
- `python -m pocket_rescue.api.client sample` - Test API connection and get sample
- `python -m pocket_rescue.api.processor <json_file>` - Test data processing

### Testing and Validation
There are no formal test suites. Validate functionality by:
1. Running commands and checking output messages
2. Verifying files are created in `saved_articles/` directory
3. Checking database creation at `saved_articles/articles.db`
4. Confirming CSV exports are generated

## Architecture Overview

This is a **modular Python package** consisting of organized modules that work together to preserve Pocket articles.

### Package Structure

```
pocket_rescue/
├── cli/           # Command-line interface
├── core/          # Core processing modules
├── api/           # Pocket API integration
└── utils/         # Shared utilities
```

### Core Components

**CLI Package** (`pocket_rescue.cli`):
- Main entry point and command orchestration
- Handles argument parsing and workflow management
- Integrates all modules into unified interface

**Core Processing** (`pocket_rescue.core`):
1. **Link Checker** (`link_checker.py`) - URL validation and analysis
2. **Content Scraper** (`content_scraper.py`) - Article text extraction
3. **Wayback Scraper** (`wayback_scraper.py`) - Internet Archive recovery
4. **Priority Filter** (`priority_filter.py`) - Article scoring and filtering
5. **Content Organizer** (`content_organizer.py`) - Folder organization and search
6. **Reading Tracker** (`reading_tracker.py`) - Progress tracking and analytics

**API Integration** (`pocket_rescue.api`):
- **Authentication** (`auth.py`) - OAuth flow with token management
- **Client** (`client.py`) - Paginated API data retrieval  
- **Processor** (`processor.py`) - Data formatting and CSV export

**Utilities** (`pocket_rescue.utils`):
- **Database** (`database.py`) - SQLite management and helpers
- **Console Utils** (`console_utils.py`) - Cross-platform compatibility

### Data Flow Architecture

**New API Workflow:**
```
Pocket API → Authentication → Data Retrieval → Processing → CSV Export
    ↓
Traditional workflow continues from CSV...
```

**Traditional Workflow:**
```
CSV Input → Link Check → Content Scraping → Wayback Recovery
                ↓
         SQLite Database ← Content Organization ← Priority Analysis
                ↓
         Search Index + Reading Tracker + Statistics
```

### Key Technical Patterns

**Package Imports**: Use relative imports within package (`from ..utils import database`)
**Module Execution**: Individual modules can be run with `-m` flag
**Database Schema**: Three main tables in SQLite:
- `articles` - Core article data and metadata
- `reading_progress` - User reading status and notes  
- `reading_sessions` - Time tracking for reading analytics

**Error Handling**: Graceful degradation with comprehensive error reporting
**Performance**: Configurable concurrency and rate limiting
**File Organization**: Category-based folder structure with search indexing

## Configuration and Customization

**Priority Rules** (`pocket_rescue/core/priority_filter.py:22-55`): 
Edit the `priority_rules` dictionary to customize scoring based on your tags.

**Category Mapping** (`pocket_rescue/core/content_organizer.py:34-44`):
Modify the `categories` dictionary to change folder organization.

**API Consumer Key** (`pocket_rescue/api/auth.py:15`):
Set `POCKET_CONSUMER_KEY` environment variable.

**Content Extraction**: Uses newspaper3k, readability-lxml, and BeautifulSoup fallback.

## New API Features

**Authentication**: Secure OAuth flow with token persistence in `~/.pocket_rescue/auth.json`
**Data Retrieval**: Handles pagination automatically with rate limiting
**Processing**: Converts API response to CSV format compatible with existing workflow
**Flexibility**: Support for different article states (unread, archive, all)

## Input Requirements

### API Workflow (New)
- **No manual export needed** - Direct API access
- **Authentication required** - One-time OAuth setup
- **Rate limited** - Respects Pocket API limits

### Traditional CSV Workflow  
- **Primary Input**: CSV export from Pocket (rename to `part_000000.csv`)
- **Expected CSV Columns**: url, title, tags, status, time_added

## Output Structure

All content is saved to `saved_articles/` directory:
- Organized category folders with markdown files
- `articles.db` - SQLite database with all metadata
- `search_index.json` - Full-text search index
- Various CSV exports for analysis and filtering

## Common Gotchas

1. **Package Structure**: Use `-m` flag for individual modules: `python -m pocket_rescue.core.link_checker`
2. **API Authentication**: First run requires browser interaction for OAuth
3. **Virtual Environment**: Always activate before running any commands
4. **Workers Parameter**: Don't exceed 20 to avoid rate limiting
5. **CSV Compatibility**: API-generated CSV works with all existing commands
6. **Priority Customization**: Edit files in `pocket_rescue/core/` directory now