#!/bin/bash

# Ghostcommit Image Protection System Deployment Script
# Date: July 12, 2026 11:00 EDT

echo "================================================================"
echo "Ghostcommit Image Protection System - Deployment"
echo "================================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
echo -e "\n${YELLOW}Checking Python version...${NC}"
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
echo "Python version: $PYTHON_VERSION"

if [[ $(echo $PYTHON_VERSION | cut -d'.' -f1) -lt 3 ]] || [[ $(echo $PYTHON_VERSION | cut -d'.' -f1) -eq 3 && $(echo $PYTHON_VERSION | cut -d'.' -f2) -lt 8 ]]; then
    echo -e "${RED}Error: Python 3.8+ required${NC}"
    exit 1
fi

# Install required packages
echo -e "\n${YELLOW}Installing required packages...${NC}"
pip3 install Pillow numpy opencv-python scikit-image flask

if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to install dependencies${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Dependencies installed${NC}"

# Create directory structure
echo -e "\n${YELLOW}Creating directory structure...${NC}"
mkdir -p test_images
mkdir -p vpi_test_results
mkdir -p vpi_analysis_results
mkdir -p quarantine
mkdir -p logs

echo -e "${GREEN}✅ Directories created${NC}"

# Generate VPI test images
echo -e "\n${YELLOW}Generating VPI test images...${NC}"
cd /Users/mitchparker/.openclaw/workspace/research/ghostcommit-image-system
python3 generate_vpi_test_images.py --output-dir ../test_images --variants 3

echo -e "${GREEN}✅ Test images generated${NC}"

# Run VPI test suite
echo -e "\n${YELLOW}Running VPI test suite...${NC}"
python3 vpi_test_suite.py --output-dir ../vpi_test_results

TEST_RESULT=$?

if [ $TEST_RESULT -eq 0 ]; then
    echo -e "${GREEN}✅ VPI Test Suite PASSED${NC}"
else
    echo -e "${RED}❌ VPI Test Suite FAILED${NC}"
fi

# Create service configuration
echo -e "\n${YELLOW}Creating service configuration...${NC}"
cat > service_config.json << EOF
{
    "detection_threshold": 0.5,
    "enable_alerts": true,
    "quarantine_threats": true,
    "max_file_size_mb": 10,
    "supported_formats": ["png", "jpg", "jpeg", "gif", "bmp", "webp"],
    "log_level": "INFO",
    "quarantine_dir": "quarantine",
    "monitoring_interval": 60
}
EOF

echo -e "${GREEN}✅ Service configuration created${NC}"

# Summary
echo -e "\n================================================================"
echo "DEPLOYMENT COMPLETE"
echo "================================================================"
echo -e "${GREEN}✅ System deployed successfully${NC}"
echo ""
echo "Next Steps:"
echo "1. Run tests: python3 vpi_test_suite.py"
echo "2. Start service: python3 image_protection_service.py --api-server"
echo "3. Scan directory: python3 image_protection_service.py --scan-dir /path/to/images"
echo ""
echo "Test images generated in: ../test_images"
echo "Test results saved to: ../vpi_test_results"
echo -e "${NC}"

exit $TEST_RESULT
