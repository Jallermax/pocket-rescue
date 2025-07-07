#!/usr/bin/env python3
"""
Script to check HTTP status codes for URLs in a CSV file.
Outputs entries with invalid responses (non-2xx status codes).
"""

import csv
import requests
import sys
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple
import time

# Setup console encoding for Windows compatibility
try:
    from ..utils.console_utils import init_console
    init_console()
except ImportError:
    pass


def is_valid_url(url: str) -> bool:
    """Check if URL has a valid format."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def check_url(row: Dict[str, str], timeout: int = 10) -> Tuple[Dict[str, str], int, str]:
    """
    Check HTTP status for a single URL.
    Returns: (row_data, status_code, error_message)
    """
    url = row['url']
    
    if not is_valid_url(url):
        return row, 0, "Invalid URL format"
    
    try:
        response = requests.get(
            url, 
            timeout=timeout,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'},
            allow_redirects=True
        )
        return row, response.status_code, ""
    except requests.exceptions.Timeout:
        return row, 0, "Timeout"
    except requests.exceptions.ConnectionError:
        return row, 0, "Connection error"
    except requests.exceptions.TooManyRedirects:
        return row, 0, "Too many redirects"
    except requests.exceptions.RequestException as e:
        return row, 0, f"Request error: {str(e)}"
    except Exception as e:
        return row, 0, f"Unknown error: {str(e)}"


def main():
    csv_file = "part_000000.csv"
    output_file = "invalid_links.csv"
    max_workers = 20
    timeout = 10
    skip_archived = True
    
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    if len(sys.argv) > 2 and sys.argv[2] == "--include-archived":
        skip_archived = False
    
    print(f"Checking links in: {csv_file}")
    print(f"Output file: {output_file}")
    print(f"Skip archived links: {skip_archived}")
    print(f"Timeout: {timeout}s, Workers: {max_workers}")
    print("-" * 50)
    
    invalid_entries = []
    total_count = 0
    skipped_count = 0
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            all_rows = list(reader)
            
            # Filter out archived entries if requested
            if skip_archived:
                rows = [row for row in all_rows if row.get('status', '').lower() != 'archive']
                skipped_count = len(all_rows) - len(rows)
            else:
                rows = all_rows
                
            total_count = len(rows)
            
        print(f"Found {total_count} entries to check")
        if skip_archived:
            print(f"Skipped {skipped_count} archived entries")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_row = {executor.submit(check_url, row, timeout): row for row in rows}
            
            # Process results as they complete
            for i, future in enumerate(as_completed(future_to_row), 1):
                row_data, status_code, error_msg = future.result()
                
                # Progress indicator
                if i % 50 == 0 or i == total_count:
                    print(f"Processed: {i}/{total_count} ({i/total_count*100:.1f}%)")
                
                # Check if response is invalid (non-2xx or error)
                if status_code == 0 or not (200 <= status_code < 300):
                    invalid_entry = row_data.copy()
                    invalid_entry['status_code'] = str(status_code)
                    invalid_entry['error'] = error_msg
                    invalid_entries.append(invalid_entry)
                    
                    print(f"INVALID: {row_data['url']} - Status: {status_code} - Error: {error_msg}")
        
        # Write invalid entries to output file
        if invalid_entries:
            fieldnames = list(invalid_entries[0].keys())
            with open(output_file, 'w', newline='', encoding='utf-8') as output:
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(invalid_entries)
            
            print(f"\nFound {len(invalid_entries)} invalid links out of {total_count} total")
            print(f"Invalid entries saved to: {output_file}")
        else:
            print(f"\nAll {total_count} links are valid!")
            
    except FileNotFoundError:
        print(f"Error: File '{csv_file}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()