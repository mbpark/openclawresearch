#!/bin/bash
# nghttp3 XRING Vulnerability Analysis Script
# This script will analyze nghttp3 source for the XRING vulnerability pattern

# Configuration
NGHTTP3_SOURCE="/tmp/nghttp3"  # Path to nghttp3 repository
OUTPUT_DIR="/tmp/nghttp3_analysis"
LOG_FILE="$OUTPUT_DIR/analysis.log"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Initialize log
echo "=== XRING Analysis Started: $(date) ===" > "$LOG_FILE"

# Function to analyze ring buffer resize patterns
analyze_ringbuf_resize() {
    local file=$1
    echo "Analyzing: $file" >> "$LOG_FILE"
    
    # Look for capacity variable usage in resize functions
    grep -n "capacity" "$file" | head -20 >> "$LOG_FILE"
    
    # Look for memcpy operations with capacity variables
    grep -n "memcpy\|memmove" "$file" >> "$LOG_FILE"
    
    # Look for truncation logic
    grep -n "trunc\|wrap\|offset" "$file" >> "$LOG_FILE"
}

# Function to detect XRing pattern
detect_xring_pattern() {
    local file=$1
    echo "Detecting XRing pattern in: $file" >> "$LOG_FILE"
    
    # Search for the vulnerable pattern: new_cap - soffset where should use old_cap
    grep -n "new_cap.*-" "$file" >> "$LOG_FILE"
    grep -n "old_cap.*-" "$file" >> "$LOG_FILE"
    
    # Look for capacity variable mixing
    if grep -q "new_cap.*soffset" "$file" && grep -q "old_cap.*soffset" "$file"; then
        echo "WARNING: Potential capacity variable mixing detected" >> "$LOG_FILE"
        return 1
    fi
    
    return 0
}

# Main analysis
main() {
    echo "Starting nghttp3 XRING analysis..." >> "$LOG_FILE"
    
    if [ ! -d "$NGHTTP3_SOURCE" ]; then
        echo "Error: nghttp3 source not found at $NGHTTP3_SOURCE" >> "$LOG_FILE"
        echo "Please clone the repository first:"
        echo "git clone https://github.com/nghttp2/nghttp3.git" >> "$LOG_FILE"
        exit 1
    fi
    
    # Analyze key files
    analyze_files=(
        "$NGHTTP3_SOURCE/lib/nghttp3_qpack.c"
        "$NGHTTP3_SOURCE/lib/nghttp3_qpack_decoder.c"
        "$NGHTTP3_SOURCE/lib/nghttp3_qpack_encoder.c"
        "$NGHTTP3_SOURCE/lib/nghttp3_qpack.h"
        "$NGHTTP3_SOURCE/lib/nghttp3_ringbuf.h"
        "$NGHTTP3_SOURCE/lib/nghttp3_ringbuf.c"
    )
    
    for file in "${analyze_files[@]}"; do
        if [ -f "$file" ]; then
            analyze_ringbuf_resize "$file"
            detect_xring_pattern "$file"
        else
            echo "File not found: $file" >> "$LOG_FILE"
        fi
    done
    
    echo "=== Analysis Completed: $(date) ===" >> "$LOG_FILE"
    echo "Analysis complete. See $LOG_FILE for results."
}

# Run main function
main "$@"
