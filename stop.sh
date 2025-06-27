#!/bin/bash

echo "Stopping Reversible Image Modification System..."

# Stop all services
docker-compose down

echo "All services stopped."
echo ""
echo "To start again, run: ./start.sh"
