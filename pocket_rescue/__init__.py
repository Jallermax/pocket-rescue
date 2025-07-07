"""
Pocket Rescue - A comprehensive toolkit for preserving Pocket articles.

This package provides tools for downloading, organizing, and managing
your saved Pocket articles before the service shuts down.
"""

__version__ = "1.0.0"
__author__ = "Pocket Rescue Contributors"

# Import main classes for convenience
try:
    from .core.content_scraper import ContentScraper
    from .core.content_organizer import ContentOrganizer
    from .core.priority_filter import PriorityFilter
    from .core.reading_tracker import ReadingTracker
    from .core.wayback_scraper import WaybackScraper
    from .api.client import PocketClient
    from .api.processor import PocketProcessor
    from .utils.database import DatabaseManager
except ImportError:
    # Some optional dependencies might not be available
    pass

__all__ = [
    'ContentScraper',
    'ContentOrganizer', 
    'PriorityFilter',
    'ReadingTracker',
    'WaybackScraper',
    'PocketClient',
    'PocketProcessor',
    'DatabaseManager'
]