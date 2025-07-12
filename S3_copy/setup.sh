#!/bin/bash

# S3 Bulk Transfer Setup Script

echo "Setting up S3 Bulk Transfer Script..."

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed."
    echo "Please install Python 3.7 or higher and try again."
    exit 1
fi

# Check Python version
python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
required_version="3.7"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "Error: Python 3.7 or higher is required. Found version: $python_version"
    exit 1
fi

echo "Python version: $python_version ✓"

# Install dependencies
echo "Installing Python dependencies..."
pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "Dependencies installed successfully ✓"
else
    echo "Error: Failed to install dependencies"
    exit 1
fi

# Make script executable
chmod +x s3_bulk_transfer.py

# Create credential files if they don't exist
if [ ! -f "source_credentials.json" ]; then
    echo "Creating source_credentials.json template..."
    cat > source_credentials.json << EOF
{
    "access_key": "YOUR_SOURCE_ACCESS_KEY",
    "secret_key": "YOUR_SOURCE_SECRET_KEY",
    "region": "us-east-1"
}
EOF
fi

echo ""
echo "Note: This script uses EC2 instance profile for destination account access."
echo "Make sure your EC2 instance has the proper IAM role attached."
echo "No destination credentials file is needed."

echo ""
echo "Setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Edit source_credentials.json with your source AWS credentials"
echo "2. Ensure your EC2 instance has proper IAM role for destination S3 access"
echo "3. Run the transfer script:"
echo "   python3 s3_bulk_transfer.py --help"
echo ""
echo "Example usage:"
echo "   python3 s3_bulk_transfer.py \\"
echo "       --source-credentials source_credentials.json \\"
echo "       --dest-region us-east-1 \\"
echo "       --source-bucket your-source-bucket \\"
echo "       --dest-bucket your-dest-bucket" 