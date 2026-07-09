#!/bin/bash

# Resilience Testing Infrastructure Setup Script

set -e

echo "=========================================="
echo "Setting up Resilience Testing Infrastructure"
echo "=========================================="

# Change to project directory
cd /Users/mitchparker/.openclaw/workspace/research/resilience

# Check if Docker is running
echo -e "\n🔍 Checking Docker availability..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "❌ Docker is not running. Please start Docker."
    exit 1
fi
echo "✅ Docker is available and running"

# Create necessary directories
echo -e "\n📁 Creating directories..."
mkdir -p checkpoints
mkdir -p logs
mkdir -p results

# Build Docker images
echo -e "\n🏗️  Building Docker images..."
docker-compose build --no-cache

# Start services in background
echo -e "\n🚀 Starting Docker services..."
docker-compose up -d

# Wait for services to be ready
echo -e "\n⏳ Waiting for services to be ready..."
sleep 10

# Check service health
echo -e "\n🏥 Checking service health..."
docker-compose ps

# Initialize database
echo -e "\n🗄️  Initializing database..."
docker-compose exec -T database psql -U testuser -d testdb -f /docker-entrypoint-initdb.d/init_db.sql

# Wait for database to be ready
echo -e "\n⏳ Waiting for database to be ready..."
sleep 5

# Verify database connection
if docker-compose exec -T database psql -U testuser -d testdb -c "SELECT 1" &> /dev/null; then
    echo "✅ Database is ready"
else
    echo "❌ Database initialization failed"
    exit 1
fi

# Test application endpoint
echo -e "\n🔗 Testing application endpoint..."
max_retries=30
retry_count=0

while [ $retry_count -lt $max_retries ]; do
    if curl -f http://localhost:8080/health &> /dev/null; then
        echo "✅ Application is responding"
        break
    fi
    retry_count=$((retry_count + 1))
    echo "Retrying ($retry_count/$max_retries)..."
    sleep 2
done

if [ $retry_count -eq $max_retries ]; then
    echo "❌ Application failed to start"
    docker-compose logs app
    exit 1
fi

# Display status
echo -e "\n=========================================="
echo "Infrastructure Setup Complete!"
echo "=========================================="
echo -e "\n📊 Available endpoints:"
echo "  - Application: http://localhost:8080"
echo "  - HAProxy LB:  http://localhost:8081"
echo "  - Prometheus:  http://localhost:9090"
echo "  - Grafana:     http://localhost:3000 (admin/admin)"

echo -e "\n🔍 View logs:"
echo "  docker-compose logs -f"

echo -e "\n🛑 Stop services:"
echo "  docker-compose down"

echo -e "\n📈 Next steps:"
echo "  1. Run resilience tests: python test_resilience.py"
echo "  2. Monitor metrics: http://localhost:9090"
echo "  3. View dashboard: http://localhost:3000"
