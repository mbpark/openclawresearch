#!/bin/bash

# Simple start script for resilience test application

echo "Starting Simple Resilience Test Application..."

# Change to project directory
cd /Users/mitchparker/.openclaw/workspace/research/resilience

# Initialize database
python3 -c "import app_simple; print('Database initialized')" 2>/dev/null || echo "Note: Database init will occur on first request"

# Start the application
echo "Starting server on port 8080..."
python3 app_simple.py &

# Wait for server to start
sleep 3

# Test if server is responding
if curl -s http://localhost:8080/health > /dev/null; then
    echo "✅ Server is running!"
    echo -e "\n📊 Available endpoints:"
    echo "  - Health: http://localhost:8080/health"
    echo "  - Metrics: http://localhost:8080/metrics"
    echo "  - Transactions: http://localhost:8080/api/transactions"
    echo "  - Checkpoints: http://localhost:8080/api/checkpoints"
    echo -e "\n🔗 Test with:"
    echo "  curl http://localhost:8080/health"
    echo "  curl -X POST http://localhost:8080/api/transactions -H 'Content-Type: application/json' -d '{\"amount\":100,\"description\":\"test\",\"user_id\":\"test\"}'"
else
    echo "❌ Server failed to start"
    exit 1
fi
