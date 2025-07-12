#!/usr/bin/env python3
"""
Test Destination S3 Access
Tests access to destination bucket using EC2 instance profile
"""

import boto3
import sys
import argparse
from botocore.exceptions import ClientError

def test_destination_access(bucket_name, region):
    """Test destination bucket access using instance profile"""
    try:
        print(f"Testing destination bucket access...")
        print(f"Bucket: {bucket_name}")
        print(f"Region: {region}")
        print("=" * 50)
        
        # Create S3 client using instance profile
        s3_client = boto3.client('s3', region_name=region)
        
        # Test 1: Head bucket
        print("1. Testing bucket access...")
        try:
            s3_client.head_bucket(Bucket=bucket_name)
            print(f"✓ Successfully accessed destination bucket '{bucket_name}'")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                print(f"✗ Destination bucket '{bucket_name}' not found")
                return False
            elif error_code == '403':
                print(f"✗ Access denied to destination bucket '{bucket_name}'")
                print("Please check:")
                print("1. EC2 instance has proper IAM role attached")
                print("2. IAM role has s3:PutObject permission")
                print("3. Bucket policy allows access")
                return False
            else:
                print(f"✗ Error accessing destination bucket: {e}")
                return False
        
        # Test 2: Put a test object
        print("\n2. Testing object upload...")
        try:
            test_key = "test-access-file.txt"
            test_content = "This is a test file to verify S3 access"
            
            s3_client.put_object(
                Bucket=bucket_name,
                Key=test_key,
                Body=test_content
            )
            print(f"✓ Successfully uploaded test object '{test_key}'")
            
            # Clean up test object
            s3_client.delete_object(Bucket=bucket_name, Key=test_key)
            print(f"✓ Successfully deleted test object '{test_key}'")
            
        except ClientError as e:
            print(f"✗ Error uploading test object: {e}")
            return False
        
        # Test 3: Test multipart upload (for large files)
        print("\n3. Testing multipart upload capability...")
        try:
            # Create multipart upload
            response = s3_client.create_multipart_upload(Bucket=bucket_name, Key="test-multipart")
            upload_id = response['UploadId']
            
            # Upload a part
            part_response = s3_client.upload_part(
                Bucket=bucket_name,
                Key="test-multipart",
                PartNumber=1,
                UploadId=upload_id,
                Body="test part content"
            )
            
            # Complete multipart upload
            s3_client.complete_multipart_upload(
                Bucket=bucket_name,
                Key="test-multipart",
                UploadId=upload_id,
                MultipartUpload={
                    'Parts': [{
                        'ETag': part_response['ETag'],
                        'PartNumber': 1
                    }]
                }
            )
            
            print("✓ Successfully tested multipart upload")
            
            # Clean up
            s3_client.delete_object(Bucket=bucket_name, Key="test-multipart")
            
        except ClientError as e:
            print(f"✗ Error testing multipart upload: {e}")
            return False
        
        print("\n" + "=" * 50)
        print("✓ All destination access tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def check_instance_profile():
    """Check if EC2 instance has instance profile"""
    try:
        # Try to get instance metadata
        import requests
        response = requests.get('http://169.254.169.254/latest/meta-data/iam/security-credentials/', timeout=5)
        if response.status_code == 200:
            role_name = response.text.strip()
            print(f"✓ EC2 instance has IAM role: {role_name}")
            return True
        else:
            print("⚠ No IAM role found on EC2 instance")
            return False
    except Exception as e:
        print(f"⚠ Could not check instance profile: {e}")
        print("This might be normal if running outside EC2")
        return True

def main():
    parser = argparse.ArgumentParser(description='Test Destination S3 Access')
    parser.add_argument('--bucket', required=True,
                       help='Destination S3 bucket name')
    parser.add_argument('--region', required=True,
                       help='AWS region for destination bucket')
    
    args = parser.parse_args()
    
    print("Destination S3 Access Test")
    print("=" * 50)
    
    # Check instance profile
    check_instance_profile()
    print()
    
    # Test destination access
    success = test_destination_access(args.bucket, args.region)
    
    if success:
        print("\n🎉 Destination access test successful!")
        sys.exit(0)
    else:
        print("\n❌ Destination access test failed!")
        print("\nTo fix this issue:")
        print("1. Ensure EC2 instance has IAM role attached")
        print("2. IAM role should have these permissions:")
        print("   - s3:PutObject")
        print("   - s3:PutObjectAcl") 
        print("   - s3:AbortMultipartUpload")
        print("   - s3:ListMultipartUploadParts")
        print("3. Check bucket policy allows access")
        sys.exit(1)

if __name__ == "__main__":
    main() 