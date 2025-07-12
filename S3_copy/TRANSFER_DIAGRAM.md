# S3 Transfer Data Flow Diagram

## 🔄 **Small Files (< 100MB) - Single Step Transfer**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Source S3     │    │   EC2 Memory    │    │ Destination S3  │
│   Bucket        │    │   (RAM Only)    │    │   Bucket        │
│                 │    │                 │    │                 │
│  file.parquet   │───▶│  In-Memory      │───▶│  file.parquet   │
│                 │    │  Buffer         │    │                 │
│                 │    │  (~50MB)        │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
    Download              Temporary              Upload
    (source_s3)          Memory Buffer         (dest_s3)
    ~50MB → RAM          (no disk)             RAM → S3
```

## 🔄 **Large Files (> 100MB) - Chunked Transfer**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Source S3     │    │   EC2 Memory    │    │ Destination S3  │
│   Bucket        │    │   (RAM Only)    │    │   Bucket        │
│                 │    │                 │    │                 │
│  large-file     │───▶│  8MB Chunks     │───▶│  large-file     │
│  (1GB)          │    │  in Memory      │    │  (1GB)          │
│                 │    │  (no disk)      │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
    Stream Download         Chunk Buffer          Multipart Upload
    (source_s3)            (8MB at a time)       (dest_s3)
    1GB → 8MB chunks       Memory only           8MB chunks → 1GB
```

## 📍 **What's Stored Where**

### ✅ **EC2 Instance Storage (Disk)**
```
/opt/s3_transfer/
├── s3_bulk_transfer.py      # Script file
├── source_credentials.json   # Credentials
├── requirements.txt          # Dependencies
├── s3_transfer.log          # Log file
└── transfer_progress.json   # Progress tracking
```

### ❌ **EC2 Instance Storage (Memory Only)**
```
RAM (Temporary):
├── Small files: File size in memory
├── Large files: 8MB chunks in memory
└── Concurrent transfers: 8MB × workers
```

### ❌ **NOT Stored on EC2**
```
❌ No temporary files
❌ No downloaded files on disk
❌ No uploaded files on disk
❌ No data persistence
```

## 🧠 **Memory Usage Examples**

### Example 1: 10 Small Files (50MB each)
```
Memory Usage: 50MB × 10 = 500MB RAM
Disk Usage: 0MB (no files stored)
Duration: ~30 seconds per file
```

### Example 2: 1 Large File (1GB)
```
Memory Usage: 8MB chunks in RAM
Disk Usage: 0MB (no files stored)
Duration: ~5 minutes for 1GB
```

### Example 3: 5TB Transfer with 10 Workers
```
Memory Usage: 8MB × 10 = 80MB RAM
Disk Usage: 0MB (no files stored)
Duration: ~2-4 hours for 5TB
```

## ⚡ **Performance Benefits**

### ✅ **Advantages**
- **No Disk I/O**: Faster than disk-based transfers
- **No Storage Requirements**: Doesn't fill up EC2 disk
- **Memory Efficient**: Only uses chunk-sized memory
- **Resume Capable**: Progress tracking without local files
- **Network Optimized**: Direct streaming

### 📊 **Speed Comparison**
```
Disk-based transfer: S3 → Disk → S3 (slower)
Memory-based transfer: S3 → RAM → S3 (faster)
```

## 🔧 **Configuration Impact**

### Chunk Size Impact:
```bash
--chunk-size 8388608    # 8MB chunks (default)
--chunk-size 16777216   # 16MB chunks (faster, more memory)
--chunk-size 4194304    # 4MB chunks (slower, less memory)
```

### Workers Impact:
```bash
--max-workers 5         # 5 concurrent (40MB RAM)
--max-workers 10        # 10 concurrent (80MB RAM)
--max-workers 20        # 20 concurrent (160MB RAM)
```

## 🛡️ **Security Benefits**

### ✅ **Security Advantages**
- **No Local Storage**: Data never touches EC2 disk
- **Memory Only**: Data only exists in RAM during transfer
- **Automatic Cleanup**: Memory freed after each transfer
- **No Temp Files**: No temporary files to secure/clean up

### 🔒 **Data Protection**
```
Source S3 → Encrypted in transit → EC2 Memory → Encrypted in transit → Destination S3
```

## 📈 **Monitoring Commands**

### Memory Monitoring:
```bash
# Watch memory usage
watch -n 1 'free -h'

# Monitor Python process
ps aux | grep s3_bulk_transfer

# Check disk usage (should stay constant)
df -h
```

### Transfer Monitoring:
```bash
# Watch transfer progress
tail -f s3_transfer.log

# Check progress file
cat transfer_progress.json
```

## 🚨 **Key Points**

1. **No Local Storage**: Data is never saved to EC2 disk
2. **Streaming Transfer**: Data flows through memory only
3. **Memory Efficient**: Uses minimal RAM for large files
4. **Resume Safe**: Progress tracking without local files
5. **Network Bound**: Transfer speed limited by network, not disk I/O
6. **Secure**: No data persistence on EC2 instance 