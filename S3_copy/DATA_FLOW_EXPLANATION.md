# Data Flow and Storage Locations

## Overview
The script uses **streaming transfer** - data flows through memory without being stored locally on the EC2 instance. Here's the detailed breakdown:

## 🔄 **Data Flow for Small Files (< 100MB)**

```
Source S3 Bucket → EC2 Memory → Destination S3 Bucket
     ↓                    ↓                    ↓
   Download           In-Memory            Upload
   (source_s3)        Buffer              (dest_s3)
```

### Step-by-Step Process:

1. **Download Phase**:
   ```python
   response = self.source_s3.get_object(Bucket=self.source_bucket, Key=source_key)
   ```
   - **Location**: Data streams from source S3 to EC2 memory
   - **Storage**: Temporary buffer in RAM (not disk)
   - **Duration**: Until upload completes

2. **Upload Phase**:
   ```python
   self.destination_s3.put_object(
       Bucket=self.destination_bucket,
       Key=dest_key,
       Body=response['Body'].read()
   )
   ```
   - **Location**: Data streams from EC2 memory to destination S3
   - **Storage**: No local storage - direct streaming
   - **Duration**: Until upload completes

## 🔄 **Data Flow for Large Files (> 100MB)**

```
Source S3 → EC2 Memory → Destination S3 (Multipart)
   ↓           ↓              ↓
Download    Chunk Buffer   Upload Parts
```

### Step-by-Step Process:

1. **Multipart Upload Initiation**:
   ```python
   response = self.destination_s3.create_multipart_upload(
       Bucket=self.destination_bucket,
       Key=dest_key
   )
   ```

2. **Chunk-by-Chunk Transfer**:
   ```python
   with self.source_s3.get_object(Bucket=self.source_bucket, Key=source_key)['Body'] as source_stream:
       while True:
           chunk = source_stream.read(self.chunk_size)  # 8MB chunks
           if not chunk:
               break
           
           # Upload each chunk
           response = self.destination_s3.upload_part(
               Bucket=self.destination_bucket,
               Key=dest_key,
               PartNumber=part_number,
               UploadId=upload_id,
               Body=chunk
           )
   ```

3. **Complete Multipart Upload**:
   ```python
   self.destination_s3.complete_multipart_upload(
       Bucket=self.destination_bucket,
       Key=dest_key,
       UploadId=upload_id,
       MultipartUpload={'Parts': parts}
   )
   ```

## 📍 **Storage Locations**

### ✅ **What IS Stored Locally**:

1. **Script Files**:
   - `s3_bulk_transfer.py` - Main script
   - `source_credentials.json` - Credentials file
   - `requirements.txt` - Dependencies

2. **Log Files**:
   - `s3_transfer.log` - Transfer logs
   - `transfer_progress.json` - Progress tracking

3. **Python Dependencies**:
   - `boto3` library
   - Other Python packages

### ❌ **What is NOT Stored Locally**:

1. **Actual Data Files**: Never stored on EC2 disk
2. **Temporary Files**: No temporary files created
3. **Downloaded Content**: Only in memory during transfer

## 🧠 **Memory Usage**

### Small Files (< 100MB):
- **Memory Usage**: File size + overhead
- **Example**: 50MB file uses ~50MB RAM during transfer
- **Duration**: Only during transfer (seconds)

### Large Files (> 100MB):
- **Memory Usage**: Chunk size (8MB default) + overhead
- **Example**: 1GB file uses ~8MB RAM during transfer
- **Duration**: Only during chunk transfer

## ⚡ **Performance Characteristics**

### Advantages:
- ✅ **No Disk I/O**: Faster than disk-based transfers
- ✅ **No Storage Requirements**: Doesn't fill up EC2 disk
- ✅ **Memory Efficient**: Only uses chunk-sized memory
- ✅ **Resume Capable**: Progress tracking without local files

### Memory Requirements:
- **Small Files**: File size in RAM
- **Large Files**: 8MB chunks in RAM
- **Concurrent Transfers**: 8MB × number of workers

## 🔧 **Configuration Options**

### Chunk Size (for large files):
```bash
python3 s3_bulk_transfer.py \
    --chunk-size 16777216  # 16MB chunks
```

### Concurrent Workers:
```bash
python3 s3_bulk_transfer.py \
    --max-workers 10  # 10 concurrent transfers
```

## 📊 **Example Memory Usage**

For a 5TB transfer with 10 workers:

```
Small Files (100MB each):
- Memory per file: 100MB
- Concurrent memory: 100MB × 10 = 1GB
- Total memory usage: ~1GB

Large Files (1GB each):
- Memory per chunk: 8MB
- Concurrent memory: 8MB × 10 = 80MB
- Total memory usage: ~80MB
```

## 🛡️ **Security Benefits**

1. **No Local Storage**: Data never touches EC2 disk
2. **Memory Only**: Data only exists in RAM during transfer
3. **Automatic Cleanup**: Memory freed after each transfer
4. **No Temp Files**: No temporary files to secure/clean up

## 🔍 **Monitoring Memory Usage**

To monitor memory usage during transfer:

```bash
# Watch memory usage
watch -n 1 'free -h'

# Monitor Python process
ps aux | grep s3_bulk_transfer
```

## 📈 **Optimization Tips**

1. **Adjust Chunk Size**: Larger chunks = less memory but more risk
2. **Adjust Workers**: More workers = more memory but faster transfer
3. **Monitor Memory**: Watch for memory pressure during transfer
4. **Instance Size**: Choose EC2 instance with sufficient RAM

## 🚨 **Important Notes**

- **No Local Storage**: Data is never saved to EC2 disk
- **Streaming Transfer**: Data flows through memory only
- **Memory Efficient**: Uses minimal RAM for large files
- **Resume Safe**: Progress tracking without local files
- **Network Bound**: Transfer speed limited by network, not disk I/O 