#!/usr/bin/env python3
"""
S3 Transfer Monitor
Monitors the progress of S3 bulk transfers
"""

import json
import time
import os
import argparse
from datetime import datetime, timedelta

def load_progress():
    """Load transfer progress from file"""
    try:
        if os.path.exists('transfer_progress.json'):
            with open('transfer_progress.json', 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading progress: {e}")
    return {}

def format_size(size_bytes):
    """Format size in human readable format"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.2f} {size_names[i]}"

def monitor_transfer():
    """Monitor transfer progress"""
    print("S3 Transfer Monitor")
    print("=" * 50)
    
    last_count = 0
    last_size = 0
    start_time = time.time()
    
    while True:
        try:
            # Load current progress
            progress = load_progress()
            current_count = len(progress)
            current_size = sum(item['size'] for item in progress.values())
            
            # Calculate statistics
            elapsed = time.time() - start_time
            files_added = current_count - last_count
            size_added = current_size - last_size
            
            if elapsed > 0:
                files_per_sec = files_added / elapsed if elapsed > 0 else 0
                speed = size_added / elapsed if elapsed > 0 else 0
            else:
                files_per_sec = 0
                speed = 0
            
            # Clear screen and display stats
            os.system('clear' if os.name == 'posix' else 'cls')
            
            print("S3 Transfer Monitor")
            print("=" * 50)
            print(f"Files transferred: {current_count}")
            print(f"Total size: {format_size(current_size)}")
            print(f"Transfer speed: {format_size(speed)}/s")
            print(f"Files per second: {files_per_sec:.2f}")
            print(f"Elapsed time: {timedelta(seconds=int(elapsed))}")
            print("=" * 50)
            
            # Show recent transfers
            if progress:
                print("\nRecent transfers:")
                sorted_items = sorted(progress.items(), 
                                   key=lambda x: x[1]['timestamp'], 
                                   reverse=True)[:10]
                
                for key, data in sorted_items:
                    timestamp = datetime.fromisoformat(data['timestamp'])
                    print(f"  {key} ({format_size(data['size'])}) - {timestamp.strftime('%H:%M:%S')}")
            
            # Update last values
            last_count = current_count
            last_size = current_size
            start_time = time.time()
            
            # Wait before next update
            time.sleep(5)
            
        except KeyboardInterrupt:
            print("\nMonitoring stopped.")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

def show_summary():
    """Show transfer summary"""
    progress = load_progress()
    
    if not progress:
        print("No transfer progress found.")
        return
    
    total_files = len(progress)
    total_size = sum(item['size'] for item in progress.values())
    
    # Calculate time range
    timestamps = [datetime.fromisoformat(item['timestamp']) for item in progress.values()]
    if timestamps:
        start_time = min(timestamps)
        end_time = max(timestamps)
        duration = end_time - start_time
    else:
        duration = timedelta(0)
    
    print("Transfer Summary")
    print("=" * 50)
    print(f"Total files: {total_files}")
    print(f"Total size: {format_size(total_size)}")
    print(f"Duration: {duration}")
    
    if duration.total_seconds() > 0:
        avg_speed = total_size / duration.total_seconds()
        print(f"Average speed: {format_size(avg_speed)}/s")
    
    print("=" * 50)

def main():
    parser = argparse.ArgumentParser(description='Monitor S3 Transfer Progress')
    parser.add_argument('--summary', action='store_true', 
                       help='Show transfer summary and exit')
    
    args = parser.parse_args()
    
    if args.summary:
        show_summary()
    else:
        monitor_transfer()

if __name__ == "__main__":
    main() 