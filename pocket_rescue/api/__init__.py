"""
Pocket API integration.

This module provides direct integration with the Pocket API:
- OAuth authentication flow
- Article retrieval from Pocket
- Data processing and CSV export
"""

# Import API classes
try:
    from .auth import PocketAuth
    from .client import PocketClient
    from .processor import PocketProcessor
except ImportError:
    # Handle missing dependencies gracefully
    pass

__all__ = [
    'PocketAuth',
    'PocketClient', 
    'PocketProcessor'
]