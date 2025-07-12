# Fix Destination S3 Access Issues

## Problem
You're getting "Access Denied" errors when trying to write to the destination bucket. This means your EC2 instance profile doesn't have the proper permissions.

## Quick Test
First, test your destination access:

```bash
python3 test_destination_access.py --bucket your-dest-bucket --region us-east-1
```

## Solution Steps

### 1. Check Current IAM Role
```bash
# Check if EC2 has IAM role
curl http://169.254.169.254/latest/meta-data/iam/security-credentials/

# If it returns a role name, you have an IAM role
# If it returns 404, you need to attach an IAM role
```

### 2. Create IAM Role (if needed)
```bash
# Create the role
aws iam create-role \
    --role-name S3TransferRole \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "ec2.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }'

# Attach S3 policy
aws iam attach-role-policy \
    --role-name S3TransferRole \
    --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

# Create instance profile
aws iam create-instance-profile \
    --instance-profile-name S3TransferProfile

# Add role to instance profile
aws iam add-role-to-instance-profile \
    --instance-profile-name S3TransferProfile \
    --role-name S3TransferRole
```

### 3. Attach IAM Role to EC2 Instance
```bash
# Get your instance ID
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)

# Attach the instance profile
aws ec2 associate-iam-instance-profile \
    --instance-id $INSTANCE_ID \
    --iam-instance-profile Name=S3TransferProfile
```

### 4. Alternative: Create Custom Policy
If you want more restrictive permissions, create a custom policy:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:PutObjectAcl",
                "s3:AbortMultipartUpload",
                "s3:ListMultipartUploadParts",
                "s3:ListBucketMultipartUploads"
            ],
            "Resource": [
                "arn:aws:s3:::your-destination-bucket",
                "arn:aws:s3:::your-destination-bucket/*"
            ]
        }
    ]
}
```

### 5. Check Bucket Policy
Ensure your destination bucket doesn't have a restrictive policy:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowEC2Access",
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::YOUR-ACCOUNT-ID:role/S3TransferRole"
            },
            "Action": [
                "s3:PutObject",
                "s3:PutObjectAcl"
            ],
            "Resource": "arn:aws:s3:::your-destination-bucket/*"
        }
    ]
}
```

### 6. Test Again
After making changes, test the access:

```bash
python3 test_destination_access.py --bucket your-dest-bucket --region us-east-1
```

## Common Issues

### Issue: "No IAM role found"
**Solution**: Attach an IAM role to your EC2 instance

### Issue: "Access denied to bucket"
**Solution**: 
1. Check IAM role permissions
2. Verify bucket policy
3. Ensure bucket name is correct

### Issue: "Bucket not found"
**Solution**: 
1. Check bucket name spelling
2. Verify bucket exists in the specified region

## Quick Commands

### Check Current Setup
```bash
# Check instance profile
curl http://169.254.169.254/latest/meta-data/iam/security-credentials/

# Test destination access
python3 test_destination_access.py --bucket your-bucket --region us-east-1

# List buckets (to verify access)
aws s3 ls
```

### Fix Common Issues
```bash
# If no IAM role, create and attach one
aws iam create-role --role-name S3TransferRole --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ec2.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
aws iam attach-role-policy --role-name S3TransferRole --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
aws iam create-instance-profile --instance-profile-name S3TransferProfile
aws iam add-role-to-instance-profile --instance-profile-name S3TransferProfile --role-name S3TransferRole
aws ec2 associate-iam-instance-profile --instance-id $(curl -s http://169.254.169.254/latest/meta-data/instance-id) --iam-instance-profile Name=S3TransferProfile
```

## Verification
After fixing, run the full transfer test:

```bash
python3 s3_bulk_transfer.py \
    --source-credentials source_credentials.json \
    --dest-region us-east-1 \
    --source-bucket your-source-bucket \
    --dest-bucket your-dest-bucket \
    --test-access
```

This should resolve the "Access Denied" error you're experiencing with the destination bucket. 