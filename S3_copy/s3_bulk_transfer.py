#!/usr/bin/env python3
"""
S3 Bulk Transfer Script
Transfers files from one AWS account to another using source credentials
"""

import boto3
import os
import sys
import json
import logging
import argparse
from datetime import datetime
from botocore.exceptions import ClientError, NoCredentialsError
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('s3_transfer.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class S3BulkTransfer:
    def __init__(self, source_credentials, destination_region, 
                 source_bucket, destination_bucket, 
                 source_prefix="", destination_prefix="",
                 max_workers=10, chunk_size=8*1024*1024):
        """
        Initialize S3 Bulk Transfer
        
        Args:
            source_credentials: Dict with source AWS credentials
            destination_region: AWS region for destination bucket
            source_bucket: Source S3 bucket name
            destination_bucket: Destination S3 bucket name
            source_prefix: Source prefix (folder path)
            destination_prefix: Destination prefix (folder path)
            max_workers: Number of concurrent transfers
            chunk_size: Multipart upload chunk size in bytes
        """
        self.source_credentials = source_credentials
        self.destination_region = destination_region
        self.source_bucket = source_bucket
        self.destination_bucket = destination_bucket
        self.source_prefix = source_prefix.rstrip('/')
        self.destination_prefix = destination_prefix.rstrip('/')
        self.max_workers = max_workers
        self.chunk_size = chunk_size
        
        # Initialize S3 clients
        self.source_s3 = boto3.client(
            's3',
            aws_access_key_id=source_credentials['access_key'],
            aws_secret_access_key=source_credentials['secret_key'],
            region_name=source_credentials.get('region', 'us-east-1')
        )
        
        # Use instance profile for destination (no credentials needed)
        self.destination_s3 = boto3.client(
            's3',
            region_name=destination_region
        )
        
        # Transfer statistics
        self.stats = {
            'total_files': 0,
            'transferred_files': 0,
            'failed_files': 0,
            'total_size': 0,
            'transferred_size': 0,
            'start_time': None,
            'end_time': None
        }
        
        # Resume functionality
        self.transfer_log_file = 'transfer_progress.json'
        self.completed_transfers = self.load_progress()
    
    def load_progress(self):
        """Load previously completed transfers for resume functionality"""
        try:
            if os.path.exists(self.transfer_log_file):
                with open(self.transfer_log_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load progress file: {e}")
        return {}
    
    def save_progress(self, key, size):
        """Save transfer progress"""
        self.completed_transfers[key] = {
            'size': size,
            'timestamp': datetime.now().isoformat()
        }
        try:
            with open(self.transfer_log_file, 'w') as f:
                json.dump(self.completed_transfers, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save progress: {e}")
    
    def test_source_access(self):
        """Test access to source bucket and list a few objects"""
        try:
            logger.info(f"Testing access to source bucket: {self.source_bucket}")
            
            # Test bucket access
            try:
                self.source_s3.head_bucket(Bucket=self.source_bucket)
                logger.info("✓ Source bucket access successful")
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == '404':
                    logger.error(f"✗ Source bucket '{self.source_bucket}' not found")
                elif error_code == '403':
                    logger.error(f"✗ Access denied to source bucket '{self.source_bucket}'")
                    logger.error("Please check:")
                    logger.error("1. Source credentials are correct")
                    logger.error("2. Source bucket name is correct")
                    logger.error("3. Source credentials have s3:ListBucket permission")
                else:
                    logger.error(f"✗ Error accessing source bucket: {e}")
                return False
            
            # Test listing objects
            try:
                response = self.source_s3.list_objects_v2(
                    Bucket=self.source_bucket,
                    MaxKeys=5,
                    Prefix=self.source_prefix
                )
                
                if 'Contents' in response:
                    logger.info(f"✓ Successfully listed {len(response['Contents'])} objects")
                    for obj in response['Contents'][:3]:  # Show first 3 objects
                        logger.info(f"  - {obj['Key']} ({obj['Size']} bytes)")
                else:
                    logger.info("✓ Bucket access successful, but no objects found with given prefix")
                
                return True
                
            except ClientError as e:
                logger.error(f"✗ Error listing objects: {e}")
                return False
                
        except Exception as e:
            logger.error(f"✗ Unexpected error testing source access: {e}")
            return False
    
    def list_source_objects(self):
        """List all objects in source bucket with prefix"""
        objects = []
        paginator = self.source_s3.get_paginator('list_objects_v2')
        
        try:
            logger.info(f"Listing objects in bucket '{self.source_bucket}' with prefix '{self.source_prefix}'")
            
            for page in paginator.paginate(
                Bucket=self.source_bucket,
                Prefix=self.source_prefix
            ):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        objects.append({
                            'key': obj['Key'],
                            'size': obj['Size'],
                            'last_modified': obj['LastModified']
                        })
            
            logger.info(f"Found {len(objects)} objects in source bucket")
            return objects
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '403':
                logger.error(f"✗ Access denied listing objects in bucket '{self.source_bucket}'")
                logger.error("Please check:")
                logger.error("1. Source credentials have s3:ListBucket permission")
                logger.error("2. Source bucket policy allows access")
                logger.error("3. Source bucket is not encrypted with customer-managed keys")
            else:
                logger.error(f"Error listing objects: {e}")
            return []
    
    def calculate_etag(self, bucket, key):
        """Calculate ETag for object (MD5 for small files, multipart ETag for large files)"""
        try:
            response = self.source_s3.head_object(Bucket=bucket, Key=key)
            return response['ETag'].strip('"')
        except ClientError:
            return None
    
    def should_skip_transfer(self, source_key, source_size):
        """Check if file should be skipped (already transferred or exists with same size)"""
        dest_key = self.get_destination_key(source_key)
        
        # Check if already in completed transfers
        if source_key in self.completed_transfers:
            if self.completed_transfers[source_key]['size'] == source_size:
                return True
        
        # Check if file exists in destination with same size
        try:
            response = self.destination_s3.head_object(Bucket=self.destination_bucket, Key=dest_key)
            if response['ContentLength'] == source_size:
                return True
        except ClientError:
            pass
        
        return False
    
    def get_destination_key(self, source_key):
        """Convert source key to destination key"""
        if self.source_prefix:
            # Remove source prefix and add destination prefix
            relative_key = source_key[len(self.source_prefix):].lstrip('/')
        else:
            relative_key = source_key
        
        if self.destination_prefix:
            return f"{self.destination_prefix}/{relative_key}"
        else:
            return relative_key
    
    def transfer_small_file(self, source_key, dest_key, size):
        """Transfer small file using download then upload"""
        try:
            # Download from source
            response = self.source_s3.get_object(Bucket=self.source_bucket, Key=source_key)
            
            # Upload to destination
            self.destination_s3.put_object(
                Bucket=self.destination_bucket,
                Key=dest_key,
                Body=response['Body'].read()
            )
            
            logger.info(f"Transferred small file: {source_key} -> {dest_key} ({size} bytes)")
            return True
        except ClientError as e:
            logger.error(f"Error transferring small file {source_key}: {e}")
            return False
    
    def transfer_large_file(self, source_key, dest_key, size):
        """Transfer large file using multipart upload"""
        try:
            # Create multipart upload
            response = self.destination_s3.create_multipart_upload(
                Bucket=self.destination_bucket,
                Key=dest_key
            )
            upload_id = response['UploadId']
            
            parts = []
            part_number = 1
            
            # Download and upload parts
            with self.source_s3.get_object(Bucket=self.source_bucket, Key=source_key)['Body'] as source_stream:
                while True:
                    chunk = source_stream.read(self.chunk_size)
                    if not chunk:
                        break
                    
                    # Upload part
                    response = self.destination_s3.upload_part(
                        Bucket=self.destination_bucket,
                        Key=dest_key,
                        PartNumber=part_number,
                        UploadId=upload_id,
                        Body=chunk
                    )
                    
                    parts.append({
                        'ETag': response['ETag'],
                        'PartNumber': part_number
                    })
                    
                    part_number += 1
            
            # Complete multipart upload
            self.destination_s3.complete_multipart_upload(
                Bucket=self.destination_bucket,
                Key=dest_key,
                UploadId=upload_id,
                MultipartUpload={'Parts': parts}
            )
            
            logger.info(f"Transferred large file: {source_key} -> {dest_key} ({size} bytes)")
            return True
            
        except ClientError as e:
            logger.error(f"Error transferring large file {source_key}: {e}")
            # Abort multipart upload if it exists
            try:
                self.destination_s3.abort_multipart_upload(
                    Bucket=self.destination_bucket,
                    Key=dest_key,
                    UploadId=upload_id
                )
            except:
                pass
            return False
    
    def transfer_file(self, obj):
        """Transfer a single file"""
        source_key = obj['key']
        size = obj['size']
        dest_key = self.get_destination_key(source_key)
        
        # Skip if already transferred
        if self.should_skip_transfer(source_key, size):
            logger.info(f"Skipping already transferred file: {source_key}")
            self.stats['transferred_files'] += 1
            self.stats['transferred_size'] += size
            return True
        
        # Choose transfer method based on file size
        # Use multipart for files larger than 100MB
        if size > 100 * 1024 * 1024:  # 100MB
            success = self.transfer_large_file(source_key, dest_key, size)
        else:
            success = self.transfer_small_file(source_key, dest_key, size)
        
        if success:
            self.stats['transferred_files'] += 1
            self.stats['transferred_size'] += size
            self.save_progress(source_key, size)
        else:
            self.stats['failed_files'] += 1
        
        return success
    
    def run_transfer(self):
        """Run the bulk transfer"""
        logger.info("Starting S3 bulk transfer...")
        self.stats['start_time'] = datetime.now()
        
        # List all objects
        objects = self.list_source_objects()
        if not objects:
            logger.error("No objects found to transfer")
            return False
        
        self.stats['total_files'] = len(objects)
        self.stats['total_size'] = sum(obj['size'] for obj in objects)
        
        logger.info(f"Total files to transfer: {self.stats['total_files']}")
        logger.info(f"Total size to transfer: {self.stats['total_size'] / (1024**3):.2f} GB")
        
        # Transfer files using thread pool
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(self.transfer_file, obj) for obj in objects]
            
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Transfer failed: {e}")
                    self.stats['failed_files'] += 1
        
        self.stats['end_time'] = datetime.now()
        self.print_summary()
        return self.stats['failed_files'] == 0
    
    def print_summary(self):
        """Print transfer summary"""
        duration = self.stats['end_time'] - self.stats['start_time']
        
        logger.info("=" * 50)
        logger.info("TRANSFER SUMMARY")
        logger.info("=" * 50)
        logger.info(f"Total files: {self.stats['total_files']}")
        logger.info(f"Transferred files: {self.stats['transferred_files']}")
        logger.info(f"Failed files: {self.stats['failed_files']}")
        logger.info(f"Total size: {self.stats['total_size'] / (1024**3):.2f} GB")
        logger.info(f"Transferred size: {self.stats['transferred_size'] / (1024**3):.2f} GB")
        logger.info(f"Duration: {duration}")
        logger.info(f"Average speed: {self.stats['transferred_size'] / duration.total_seconds() / (1024**2):.2f} MB/s")
        logger.info("=" * 50)

def load_credentials_from_file(file_path):
    """Load AWS credentials from JSON file"""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading credentials from {file_path}: {e}")
        return None

def validate_source_credentials(credentials):
    """Validate source credentials format"""
    required_keys = ['access_key', 'secret_key']
    for key in required_keys:
        if key not in credentials:
            logger.error(f"Missing required credential key: {key}")
            return False
    return True

def main():
    parser = argparse.ArgumentParser(description='S3 Bulk Transfer between AWS Accounts')
    parser.add_argument('--source-credentials', required=True, 
                       help='Path to source credentials JSON file')
    parser.add_argument('--dest-region', required=True,
                       help='AWS region for destination bucket')
    parser.add_argument('--source-bucket', required=True,
                       help='Source S3 bucket name')
    parser.add_argument('--dest-bucket', required=True,
                       help='Destination S3 bucket name')
    parser.add_argument('--source-prefix', default='',
                       help='Source prefix (folder path)')
    parser.add_argument('--dest-prefix', default='',
                       help='Destination prefix (folder path)')
    parser.add_argument('--max-workers', type=int, default=10,
                       help='Number of concurrent transfers')
    parser.add_argument('--chunk-size', type=int, default=8*1024*1024,
                       help='Multipart upload chunk size in bytes')
    parser.add_argument('--test-access', action='store_true',
                       help='Test source bucket access before starting transfer')
    
    args = parser.parse_args()
    
    # Load source credentials
    source_creds = load_credentials_from_file(args.source_credentials)
    
    if not source_creds:
        logger.error("Failed to load source credentials")
        sys.exit(1)
    
    # Validate source credentials
    if not validate_source_credentials(source_creds):
        logger.error("Invalid source credentials format")
        sys.exit(1)
    
    # Create transfer object
    transfer = S3BulkTransfer(
        source_credentials=source_creds,
        destination_region=args.dest_region,
        source_bucket=args.source_bucket,
        destination_bucket=args.dest_bucket,
        source_prefix=args.source_prefix,
        destination_prefix=args.dest_prefix,
        max_workers=args.max_workers,
        chunk_size=args.chunk_size
    )
    
    # Test access if requested
    if args.test_access:
        logger.info("Testing source bucket access...")
        if not transfer.test_source_access():
            logger.error("Source access test failed. Please fix the issues above before proceeding.")
            sys.exit(1)
        logger.info("Source access test passed. Proceeding with transfer...")
    
    # Run transfer
    success = transfer.run_transfer()
    
    if success:
        logger.info("Transfer completed successfully!")
        sys.exit(0)
    else:
        logger.error("Transfer completed with errors!")
        sys.exit(1)

if __name__ == "__main__":
    main() 