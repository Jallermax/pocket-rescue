#!/usr/bin/env python3
"""
Console utilities for Windows compatibility.
Handles encoding issues and provides cross-platform console support.
"""

import sys
import os
import locale


def setup_console_encoding():
    """Setup console encoding for Windows compatibility."""
    if sys.platform.startswith('win'):
        try:
            # Try to set UTF-8 encoding on Windows
            import codecs
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
            sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)
        except (AttributeError, OSError):
            # Fallback to default encoding
            pass
            
        try:
            # Set console code page to UTF-8 on Windows
            os.system('chcp 65001 >nul 2>&1')
        except:
            pass


def safe_print(*args, **kwargs):
    """Print function that handles encoding errors gracefully."""
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        # Fallback to ASCII-safe output
        safe_args = []
        for arg in args:
            if isinstance(arg, str):
                # Replace problematic characters with ASCII equivalents
                safe_arg = arg.encode('ascii', 'replace').decode('ascii')
                safe_args.append(safe_arg)
            else:
                safe_args.append(str(arg))
        print(*safe_args, **kwargs)


def get_safe_filename(filename):
    """Create Windows-safe filename."""
    if sys.platform.startswith('win'):
        # Windows filename restrictions
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Remove trailing dots and spaces
        filename = filename.rstrip('. ')
        
        # Limit length
        if len(filename) > 200:
            filename = filename[:200]
            
    return filename


def init_console():
    """Initialize console with proper encoding."""
    setup_console_encoding()
    
    # Set locale for better Unicode support
    try:
        locale.setlocale(locale.LC_ALL, '')
    except locale.Error:
        pass