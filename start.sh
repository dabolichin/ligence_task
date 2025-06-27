#!/bin/bash

set -e  # Exit on any error

echo "Starting Reversible Image Modification System..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "ERROR: Docker is not running. Please start Docker first."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "ERROR: docker-compose not found. Please install Docker Compose."
    exit 1
fi

echo "Building and starting services..."

# Stop any existing containers
docker-compose down 2>/dev/null || true

# Build and start all services
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

echo "Waiting for services to start..."

# Wait for services to be accessible
timeout=90
elapsed=0
web_ready=false
image_ready=false
verification_ready=false

while [ $elapsed -lt $timeout ]; do
    if ! $web_ready && curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "Web Interface ready (port 8000)"
        web_ready=true
    fi

    if ! $image_ready && curl -s http://localhost:8001/api/health > /dev/null 2>&1; then
        echo "Image Processing Service ready (port 8001)"
        image_ready=true
    fi

    if ! $verification_ready && curl -s http://localhost:8002/api/health > /dev/null 2>&1; then
        echo "Verification Service ready (port 8002)"
        verification_ready=true
    fi

    if $web_ready && $image_ready && $verification_ready; then
        break
    fi

    sleep 3
    elapsed=$((elapsed + 3))
    echo "Still starting... ($elapsed/${timeout}s)"
done

echo ""
if $web_ready && $image_ready && $verification_ready; then
    echo "All services are running successfully!"
    echo ""
    echo "Open your browser and go to:"
    echo "  Main Interface: http://localhost:8000"
    echo ""
    echo "System Information:"
    echo "  Upload JPEG, PNG, or BMP images (max 100MB)"
    echo "  System generates 100 reversible variants per image"
    echo ""
    echo "API Documentation (OpenAPI/Swagger):"
    echo "  http://localhost:8001/docs (Image Processing)"
    echo "  http://localhost:8002/docs (Verification Service)"
else
    echo "WARNING: Some services may still be starting up:"
    echo "  Web Interface: $(if $web_ready; then echo "Ready"; else echo "Not ready"; fi)"
    echo "  Image Processing: $(if $image_ready; then echo "Ready"; else echo "Not ready"; fi)"
    echo "  Verification: $(if $verification_ready; then echo "Ready"; else echo "Not ready"; fi)"
    echo ""
    echo "Check service status:"
    echo "  docker-compose ps"
    echo "  docker-compose logs"
    echo ""
    echo "Try opening: http://localhost:8000"
fi
