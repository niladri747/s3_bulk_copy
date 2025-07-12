# S3 Access Troubleshooting Guide

## Common Access Denied Issues

### 1. Test Your Access First

Before running the full transfer, test your access:

```bash
# Test source bucket access
python3 test_access.py --credentials source_credentials.json --bucket your-source-bucket

# Test with the main script
python3 s3_bulk_transfer.py \
    --source-credentials source_credentials.json \
    --dest-region us-east-1 \
    --source-bucket your-source-bucket \
    --dest-bucket your-dest-bucket \
    --test-access
```

### 2. Common Issues and Solutions

#### Issue: "Access Denied" Error during CopyObject

**Root Cause**: This error occurs when the source credentials don't have sufficient permissions to allow their objects to be accessed by the destination account.

**Possible Causes:**

1. **Insufficient Source Permissions**
   - Source credentials need these permissions:
     ```json
     {
       "Version": "2012-10-17",
       "Statement": [
         {
           "Effect": "Allow",
           "Action": [
             "s3:GetObject",
             "s3:ListBucket",
             "s3:GetObjectVersion"
           ],
           "Resource": [
             "arn:aws:s3:::source-bucket-name",
             "arn:aws:s3:::source-bucket-name/*"
           ]
         }
       ]
     }
     ```

2. **Bucket Policy Restrictions**
   - Source bucket policy might deny cross-account access
   - Check if bucket policy allows the destination account to access objects

3. **Encryption Issues**
   - If source bucket uses customer-managed KMS keys, source credentials need KMS permissions
   - Check if bucket uses SSE-KMS encryption

4. **Cross-Account Access**
   - Source bucket must allow destination account to access objects
   - May need bucket policy to allow cross-account access

#### Issue: "Access Denied" Error during ListBucket

**Possible Causes:**

1. **Incorrect Bucket Name**
   - Double-check the bucket name spelling
   - Ensure you're using the correct bucket name (not the ARN)

2. **Wrong Region**
   - Verify the bucket is in the region specified in credentials
   - Check bucket location: `aws s3api get-bucket-location --bucket your-bucket`

3. **Insufficient Permissions**
   - Source credentials need `s3:ListBucket` permission

4. **Bucket Policy Restrictions**
   - Check if bucket has a restrictive policy
   - Verify bucket policy allows your account access

#### Issue: "Bucket Not Found"

**Solutions:**
- Verify bucket name is correct
- Check if bucket exists in the specified region
- Ensure bucket is not deleted or suspended

#### Issue: "Invalid Credentials"

**Solutions:**
- Verify access key and secret key are correct
- Check if credentials are expired
- Ensure credentials are for the correct AWS account

### 3. Step-by-Step Debugging

#### Step 1: Verify Credentials Format
```bash
cat source_credentials.json
```
Should look like:
```json
{
    "access_key": "AKIA...",
    "secret_key": "your-secret-key",
    "region": "us-east-1"
}
```

#### Step 2: Test Basic S3 Access
```bash
python3 test_access.py --credentials source_credentials.json --bucket your-bucket
```

#### Step 3: Check Bucket Location
```bash
# If you have AWS CLI configured
aws s3api get-bucket-location --bucket your-bucket-name
```

#### Step 4: Test with AWS CLI
```bash
# Test listing objects
aws s3 ls s3://your-bucket-name/ --profile your-profile

# Test getting an object
aws s3 cp s3://your-bucket-name/some-file.txt ./test-file.txt --profile your-profile
```

### 4. Cross-Account Access Issues

If accessing a bucket in a different AWS account:

1. **Bucket Policy**: Ensure bucket policy allows your account
2. **IAM User/Role**: Verify IAM entity has proper permissions
3. **Account ID**: Double-check you're using the correct account credentials

### 5. Network and Connectivity Issues

1. **VPC Endpoints**: If in VPC, ensure S3 endpoints are configured
2. **Security Groups**: Check if security groups allow S3 access
3. **Internet Gateway**: Ensure EC2 instance can reach S3

### 6. Encryption and Security Issues

1. **SSE-KMS**: If bucket uses KMS encryption, ensure credentials have KMS permissions
2. **SSE-S3**: Usually works with standard S3 permissions
3. **Customer-Managed Keys**: Requires additional KMS permissions

### 7. Common Error Messages

#### "Access Denied"
- Check permissions and bucket policy
- Verify credentials are correct
- Ensure bucket name is correct

#### "NoSuchBucket"
- Bucket doesn't exist
- Wrong region
- Bucket name typo

#### "InvalidAccessKeyId"
- Access key is incorrect
- Credentials file is malformed

#### "SignatureDoesNotMatch"
- Secret key is incorrect
- Clock synchronization issue

### 8. Testing Commands

#### Test with boto3 directly:
```python
import boto3
import json

# Load credentials
with open('source_credentials.json', 'r') as f:
    creds = json.load(f)

# Create client
s3 = boto3.client(
    's3',
    aws_access_key_id=creds['access_key'],
    aws_secret_access_key=creds['secret_key'],
    region_name=creds['region']
)

# Test access
try:
    response = s3.list_objects_v2(Bucket='your-bucket', MaxKeys=1)
    print("Access successful!")
except Exception as e:
    print(f"Access failed: {e}")
```

### 9. Getting Help

If you're still having issues:

1. **Check the logs**: Look at `s3_transfer.log` for detailed error messages
2. **Run with debug**: Use `--test-access` flag to get detailed diagnostics
3. **Verify with AWS Console**: Try accessing the bucket through AWS Console
4. **Check IAM**: Verify the IAM user/role has proper permissions

### 10. Quick Fixes

#### For "Access Denied":
```bash
# 1. Test basic access
python3 test_access.py --credentials source_credentials.json --bucket your-bucket

# 2. If that fails, check credentials
cat source_credentials.json

# 3. Test with AWS CLI
aws s3 ls s3://your-bucket/ --profile your-profile
```

#### For "Bucket Not Found":
```bash
# 1. List all buckets to see available ones
python3 test_access.py --credentials source_credentials.json --bucket dummy-bucket

# 2. Check bucket name spelling
# 3. Verify bucket exists in the specified region
```

Remember: The most common issues are incorrect bucket names, wrong regions, or insufficient permissions. Start with the basic access test to identify the specific problem. 