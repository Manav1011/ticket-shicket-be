#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================"
echo "Starting Ticket Shicket Dependencies"
echo "============================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
log_info "Checking prerequisites..."

if ! command_exists docker; then
    log_error "Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command_exists uv; then
    log_warn "uv is not installed. Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

# Step 1: Start Docker services
log_info "Starting Docker services (postgres, redis, localstack)..."
docker compose up -d

# Step 2: Wait for services to be healthy
log_info "Waiting for services to be healthy..."

wait_for_postgres() {
    echo "Waiting for PostgreSQL..."
    local max_attempts=30
    local attempt=1
    while [ $attempt -le $max_attempts ]; do
        if docker exec ticket_shicket_postgres pg_isready -U testuser -d testdb >/dev/null 2>&1; then
            echo "PostgreSQL is ready!"
            return 0
        fi
        echo "  Attempt $attempt/$max_attempts..."
        sleep 2
        attempt=$((attempt + 1))
    done
    log_error "PostgreSQL failed to start after $max_attempts attempts"
    return 1
}

wait_for_redis() {
    echo "Waiting for Redis..."
    local max_attempts=15
    local attempt=1
    while [ $attempt -le $max_attempts ]; do
        if docker exec ticket_shicket_redis redis-cli ping 2>/dev/null | grep -q "PONG"; then
            echo "Redis is ready!"
            return 0
        fi
        echo "  Attempt $attempt/$max_attempts..."
        sleep 1
        attempt=$((attempt + 1))
    done
    log_error "Redis failed to start after $max_attempts attempts"
    return 1
}

wait_for_localstack() {
    echo "Waiting for LocalStack S3..."
    local max_attempts=30
    local attempt=1
    # LocalStack takes longer to start
    sleep 5
    while [ $attempt -le $max_attempts ]; do
        if curl -s "http://localhost:4566/_localstack/health" >/dev/null 2>&1; then
            echo "LocalStack S3 is ready!"
            return 0
        fi
        echo "  Attempt $attempt/$max_attempts..."
        sleep 2
        attempt=$((attempt + 1))
    done
    log_warn "LocalStack S3 may not be fully ready, but continuing..."
    return 0
}

# Wait for all services
if ! wait_for_postgres; then
    log_error "PostgreSQL healthcheck failed"
    exit 1
fi

if ! wait_for_redis; then
    log_error "Redis healthcheck failed"
    exit 1
fi

wait_for_localstack

# Step 3: Install dependencies if needed
log_info "Ensuring dependencies are installed..."
uv sync

# Step 4: Run migrations
log_info "Running database migrations..."
uv run python main.py migrate

# Step 5: Create LocalStack S3 bucket if it doesn't exist
log_info "Ensuring LocalStack S3 bucket exists..."
aws --endpoint-url=http://localhost:4566 s3 mb s3://ticket-shicket-media 2>/dev/null || true

# Step 6: Show status
echo ""
echo "============================================"
log_info "All dependencies ready!"
echo "============================================"
echo ""
echo "Services:"
echo "  PostgreSQL  - localhost:5432"
echo "  Redis       - localhost:6379"
echo "  LocalStack  - localhost:4566"
echo ""
echo "Next: Run 'uv run python main.py run --debug' to start the server"
echo ""
echo "API Docs:    http://localhost:8080/docs"
echo "Health:      http://localhost:8080/healthcheck"
echo ""