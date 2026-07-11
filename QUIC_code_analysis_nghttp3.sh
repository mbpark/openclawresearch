#!/bin/bash

# Script to download and analyze nghttp3 QPACK implementation

cd /Users/mitchparker/.openclaw/workspace/research

# Create nghttp3 directory if it doesn't exist
mkdir -p nghttp3
cd nghttp3

# Try to get the latest commit hash
echo "Fetching nghttp3 repository metadata..."
LATEST_COMMIT=$(curl -s https://api.github.com/repos/nghttp2/nghttp3/commits/master | grep '"sha"' | head -1 | cut -d'"' -f4)

if [ -z "$LATEST_COMMIT" ]; then
    echo "Failed to get latest commit"
    exit 1
fi

echo "Latest commit: $LATEST_COMMIT"

# Download individual files using GitHub API
files=(
    "lib/nghttp3_qpack.c"
    "lib/nghttp3_qpack_decoder.c"
    "lib/nghttp3_qpack_encoder.c"
    "lib/nghttp3_qpack.h"
    "lib/nghttp3_qpack_dtable.h"
)

for file in "${files[@]}"; do
    echo "Downloading $file..."
    curl -s -L "https://raw.githubusercontent.com/nghttp2/nghttp3/$LATEST_COMMIT/$file" -o "$file"
    if [ $? -eq 0 ]; then
        echo "✓ $file downloaded"
    else
        echo "✗ Failed to download $file"
    fi
done

# Analyze ring buffer implementation
echo ""
echo "=== Analyzing ring buffer implementation ==="
grep -n "resize\|ring\|dtable" lib/nghttp3_qpack.c | head -20

# Look for potential vulnerability patterns
echo ""
echo "=== Searching for capacity comparison patterns ==="
grep -n -E "(capacity|resize)" lib/nghttp3_qpack.c | head -30

# Download header files for context
echo ""
echo "=== Checking header files ==="
grep -n "typedef.*{" lib/nghttp3_qpack.h | head -10
