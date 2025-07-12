#!/usr/bin/env python3
"""
S3 Access Test Script
Tests access to S3 buckets using provided credentials
"""

import boto3
import json
import sys
import argparse
from botocore.exceptions import ClientError, NoCredentialsError

def test_s3_access(credentials_file, bucket_name, region=None):
    """Test S3 access with given credentials"""
    try:
        # Load credentials
        with open(credentials_file, 'r') as f:
            creds = json.load(f)
        
        print(f"Testing access to bucket: {bucket_name}")
        print(f"Using credentials from: {credentials_file}")
        print(f"Region: {region or creds.get('region', 'us-east-1')}")
        print("=" * 50)
        
        # Create S3 client
        s3_client = boto3.client(
            's3',
            aws_access_key_id=creds['access_key'],
            aws_secret_access_key=creds['secret_key'],
            region_name=region or creds.get('region', 'us-east-1')
        )
        
        # Test 1: List buckets
        print("1. Testing list buckets...")
        try:
            response = s3_client.list_buckets()
            print(f"✓ Successfully listed {len(response['Buckets'])} buckets")
            bucket_names = [b['Name'] for b in response['Buckets']]
            if bucket_name in bucket_names:
                print(f"✓ Target bucket '{bucket_name}' found in bucket list")
            else:
                print(f"⚠ Target bucket '{bucket_name}' NOT found in bucket list")
                print(f"Available buckets: {bucket_names[:5]}...")
        except ClientError as e:
            print(f"✗ Error listing buckets: {e}")
            return False
        
        # Test 2: Head bucket
        print("\n2. Testing head bucket...")
        try:
            s3_client.head_bucket(Bucket=bucket_name)
            print(f"✓ Successfully accessed bucket '{bucket_name}'")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                print(f"✗ Bucket '{bucket_name}' not found")
            elif error_code == '403':
                print(f"✗ Access denied to bucket '{bucket_name}'")
                print("Possible causes:")
                print("  - Bucket name is incorrect")
                print("  - Credentials don't have s3:ListBucket permission")
                print("  - Bucket policy denies access")
            else:
                print(f"✗ Error accessing bucket: {e}")
            return False
        
        # Test 3: List objects
        print("\n3. Testing list objects...")
        try:
            response = s3_client.list_objects_v2(
                Bucket=bucket_name,
                MaxKeys=5
            )
            
            if 'Contents' in response:
                print(f"✓ Successfully listed {len(response['Contents'])} objects")
                print("Sample objects:")
                for obj in response['Contents'][:3]:
                    print(f"  - {obj['Key']} ({obj['Size']} bytes)")
            else:
                print("✓ Bucket access successful, but bucket is empty")
                
        except ClientError as e:
            print(f"✗ Error listing objects: {e}")
            return False
        
        # Test 4: Get bucket location
        print("\n4. Testing get bucket location...")
        try:
            response = s3_client.get_bucket_location(Bucket=bucket_name)
            location = response['LocationConstraint']
            if location is None:
                location = 'us-east-1'
            print(f"✓ Bucket location: {location}")
        except ClientError as e:
            print(f"✗ Error getting bucket location: {e}")
        
        print("\n" + "=" * 50)
        print("✓ All tests passed! Access to source bucket is working.")
        return True
        
    except FileNotFoundError:
        print(f"✗ Credentials file '{credentials_file}' not found")
        return False
    except json.JSONDecodeError:
        print(f"✗ Invalid JSON in credentials file '{credentials_file}'")
        return False
    except KeyError as e:
        print(f"✗ Missing required field in credentials: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Test S3 Access')
    parser.add_argument('--credentials', required=True,
                       help='Path to credentials JSON file')
    parser.add_argument('--bucket', required=True,
                       help='S3 bucket name to test')
    parser.add_argument('--region',
                       help='AWS region (optional, will use region from credentials if not specified)')
    
    args = parser.parse_args()
    
    success = test_s3_access(args.credentials, args.bucket, args.region)
    
    if success:
        print("\n🎉 Access test successful!")
        sys.exit(0)
    else:
        print("\n❌ Access test failed!")
        sys.exit(1)

if __name__ == "__main__":
    main() 