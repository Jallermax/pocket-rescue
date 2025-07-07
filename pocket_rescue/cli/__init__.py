"""
Command-line interface for Pocket Rescue.

This module provides the main CLI entry point and command handling.
"""

# Import CLI classes
try:
    from .main import PocketRescueCLI
except ImportError:
    # Handle missing dependencies gracefully
    pass

__all__ = [
    'PocketRescueCLI'
]