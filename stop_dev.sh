#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Stopping all services..."

# Stop docker services but preserve volumes
docker compose down

echo ""
echo "Services stopped. Data volumes preserved."
echo "To wipe all data: docker compose down -v"
echo "To start again:   ./start_dev.sh"