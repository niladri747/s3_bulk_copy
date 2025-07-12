# S3 Bulk Transfer Script

A robust Python script for transferring large amounts of data (5+ TB) between AWS S3 buckets across different AWS accounts using EC2 instance profile for secure destination access.

## Features

- **Cross-Account Transfer**: Transfer data between different AWS accounts using source credentials
- **EC2 Instance Profile**: Uses EC2 instance profile for destination account (no credentials needed)
- **Resume Capability**: Automatically resumes interrupted transfers
- **Concurrent Transfers**: Multi-threaded transfers for optimal performance
- **Large File Support**: Multipart uploads for files larger than 100MB
- **Progress Tracking**: Detailed logging and progress tracking
- **Error Handling**: Comprehensive error handling and retry logic
- **Size Verification**: Skips already transferred files by checking sizes

## Prerequisites

- Python 3.7 or higher
- AWS credentials for source account only
- EC2 instance in destination account with proper IAM role
- Sufficient IAM permissions

## Installation

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up source credentials:**
   - Copy `source_credentials.json` template
   - Fill in your source AWS credentials
   - Keep this file secure and never commit it to version control

3. **Configure EC2 Instance Profile:**
   - Ensure your EC2 instance has an IAM role attached
   - The role should have S3 write permissions for the destination bucket

## IAM Permissions Required

### Source Account Permissions
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

### Destination Account (EC2 Instance Profile)
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
                "arn:aws:s3:::destination-bucket-name",
                "arn:aws:s3:::destination-bucket-name/*"
            ]
        }
    ]
}
```

## Usage

### Basic Usage
```bash
python s3_bulk_transfer.py \
    --source-credentials source_credentials.json \
    --dest-region us-east-1 \
    --source-bucket source-bucket-name \
    --dest-bucket destination-bucket-name
```

### Advanced Usage
```bash
python s3_bulk_transfer.py \
    --source-credentials source_credentials.json \
    --dest-region us-west-2 \
    --source-bucket source-bucket-name \
    --dest-bucket destination-bucket-name \
    --source-prefix "folder/subfolder" \
    --dest-prefix "backup/2024" \
    --max-workers 20 \
    --chunk-size 16777216
```

### Parameters

- `--source-credentials`: Path to source AWS credentials JSON file
- `--dest-region`: AWS region for destination bucket
- `--source-bucket`: Source S3 bucket name
- `--dest-bucket`: Destination S3 bucket name
- `--source-prefix`: Source prefix (folder path) - optional
- `--dest-prefix`: Destination prefix (folder path) - optional
- `--max-workers`: Number of concurrent transfers (default: 10)
- `--chunk-size`: Multipart upload chunk size in bytes (default: 8MB)

## Security Benefits

### Using EC2 Instance Profile
- **No Credential Storage**: No need to store destination credentials
- **Automatic Rotation**: IAM roles handle credential rotation
- **Least Privilege**: Only grant necessary S3 permissions
- **Audit Trail**: All access is logged through CloudTrail

### Setup Steps for EC2
1. **Create IAM Role:**
   ```bash
   aws iam create-role --role-name S3TransferRole --assume-role-policy-document '{
     "Version": "2012-10-17",
     "Statement": [{
       "Effect": "Allow",
       "Principal": {"Service": "ec2.amazonaws.com"},
       "Action": "sts:AssumeRole"
     }]
   }'
   ```

2. **Attach S3 Policy:**
   ```bash
   aws iam attach-role-policy --role-name S3TransferRole --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
   ```

3. **Create Instance Profile:**
   ```bash
   aws iam create-instance-profile --instance-profile-name S3TransferProfile
   aws iam add-role-to-instance-profile --instance-profile-name S3TransferProfile --role-name S3TransferRole
   ```

4. **Attach to EC2 Instance:**
   ```bash
   aws ec2 associate-iam-instance-profile --instance-id i-1234567890abcdef0 --iam-instance-profile Name=S3TransferProfile
   ```

## Performance Optimization

### For 5TB Transfer

1. **EC2 Instance Recommendations:**
   - Instance Type: c5.2xlarge or higher
   - Storage: At least 100GB EBS volume
   - Network: Enhanced networking enabled

2. **Concurrent Transfers:**
   - Start with 10-20 concurrent transfers
   - Monitor network and CPU usage
   - Adjust based on performance

3. **Chunk Size:**
   - Default 8MB works well for most cases
   - For very large files (>1GB), consider 16MB chunks

### Example for 5TB Transfer
```bash
python s3_bulk_transfer.py \
    --source-credentials source_credentials.json \
    --dest-region us-east-1 \
    --source-bucket my-source-bucket \
    --dest-bucket my-dest-bucket \
    --max-workers 15 \
    --chunk-size 16777216
```

## Monitoring and Logging

The script provides comprehensive logging:

- **Console Output**: Real-time progress updates
- **Log File**: `s3_transfer.log` with detailed logs
- **Progress File**: `transfer_progress.json` for resume functionality

### Monitoring Commands
```bash
# Watch transfer progress
tail -f s3_transfer.log

# Check transfer statistics
python -c "import json; print(json.dumps(json.load(open('transfer_progress.json')), indent=2))"

# Real-time monitoring
python3 monitor_transfer.py
```

## Resume Functionality

The script automatically handles interrupted transfers:

1. **Progress Tracking**: Saves completed transfers to `transfer_progress.json`
2. **Size Verification**: Checks file sizes to avoid re-transferring
3. **Automatic Resume**: Restart the script to resume from where it left off

## Error Handling

The script handles various error scenarios:

- **Network Issues**: Automatic retry for transient failures
- **Permission Errors**: Clear error messages for IAM issues
- **Large File Timeouts**: Multipart upload with proper cleanup
- **Disk Space**: Monitors available space

## Security Best Practices

1. **Credential Management:**
   - Only store source credentials securely
   - Use IAM roles for destination access
   - Rotate credentials regularly

2. **Network Security:**
   - Use VPC endpoints for S3 access
   - Configure security groups appropriately
   - Monitor network traffic

3. **Data Protection:**
   - Enable S3 encryption
   - Use bucket policies for access control
   - Monitor access logs

## Troubleshooting

### Common Issues

1. **Permission Denied:**
   - Verify source IAM permissions
   - Check EC2 instance profile permissions
   - Ensure bucket policies are correct

2. **Slow Transfer Speed:**
   - Increase `--max-workers`
   - Check network bandwidth
   - Verify instance type

3. **Memory Issues:**
   - Reduce `--max-workers`
   - Increase instance memory
   - Monitor system resources

### Debug Mode
```bash
# Enable debug logging
export PYTHONPATH=.
python -c "
import logging
logging.getLogger().setLevel(logging.DEBUG)
import s3_bulk_transfer
"
```

## Cost Optimization

1. **Data Transfer Costs:**
   - Use same region when possible
   - Consider S3 Transfer Acceleration
   - Monitor transfer costs

2. **EC2 Costs:**
   - Use spot instances for non-critical transfers
   - Right-size instances based on workload
   - Stop instances when not in use

## Example Transfer Scenarios

### Scenario 1: Full Bucket Transfer
```bash
python s3_bulk_transfer.py \
    --source-credentials source_creds.json \
    --dest-region us-east-1 \
    --source-bucket production-data \
    --dest-bucket backup-data
```

### Scenario 2: Specific Folder Transfer
```bash
python s3_bulk_transfer.py \
    --source-credentials source_creds.json \
    --dest-region us-west-2 \
    --source-bucket production-data \
    --dest-bucket backup-data \
    --source-prefix "logs/2024" \
    --dest-prefix "archive/logs"
```

### Scenario 3: High-Performance Transfer
```bash
python s3_bulk_transfer.py \
    --source-credentials source_creds.json \
    --dest-region us-east-1 \
    --source-bucket large-dataset \
    --dest-bucket backup-dataset \
    --max-workers 25 \
    --chunk-size 33554432
```

## Support

For issues or questions:
1. Check the log files for detailed error messages
2. Verify AWS credentials and permissions
3. Test with a small subset of files first
4. Monitor system resources during transfer

## License

This script is provided as-is for educational and operational purposes. 