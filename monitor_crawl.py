#!/usr/bin/env python3
"""
Monitor the crawl progress by tailing the log file
"""

import subprocess
import sys

def monitor_crawl():
    """Monitor crawl progress"""
    print("🔍 Monitoring crawl progress...")
    print("Press Ctrl+C to stop monitoring\n")
    
    # Key patterns to highlight
    patterns = [
        "FIRST BATCH UPLOAD VERIFICATION",
        "Upload verification PASSED",
        "Upload verification FAILED", 
        "PROGRESS UPDATE",
        "CRAWL SUMMARY",
        "Successfully upserted",
        "Skipping unchanged document",
        "Document content changed",
        "CRITICAL",
        "ERROR"
    ]
    
    # Create grep pattern
    grep_pattern = "|".join(patterns)
    
    try:
        # Run grep to filter relevant log lines
        cmd = f"tail -f test_crawl.log | grep -E '{grep_pattern}' --color=always"
        subprocess.run(cmd, shell=True)
    except KeyboardInterrupt:
        print("\n\n✅ Monitoring stopped")

if __name__ == "__main__":
    monitor_crawl()