"""
Utility functions and helpers for Pocket Rescue.

This module contains shared utilities:
- Console utilities for cross-platform compatibility
- Database management and helpers
"""

# Import utility classes
try:
    from .database import DatabaseManager
    from . import console_utils
except ImportError:
    # Handle missing dependencies gracefully
    pass

__all__ = [
    'DatabaseManager',
    'console_utils'
]