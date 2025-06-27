# Reversible Image Modification System

A distributed system for applying and verifying reversible image modifications.

## Quick Start

1. **Prerequisites**: Install Docker and Docker Compose
2. **Start**: `./start.sh`
3. **Stop**: `./stop.sh`
4. **Open browser**: Go to http://localhost:8000

## Usage

### Web Interface
- **Main Interface**: http://localhost:8000
- **Upload images** using the file input
- **Click "Modify"** to process and generate 100 variants
- **View results** in the three-panel interface:
  - Images Modified (left)
  - Modifications table (center)
  - Verification Statistics (right)

## Services

- **Web Interface**: Port 8000 - Main user interface
- **Image Processing**: Port 8001 - Handles image modifications
- **Verification Service**: Port 8002 - Verifies modification reversibility

## API Documentation

OpenAPI/Swagger documentation available at:
- Image Processing API: http://localhost:8001/docs
- Verification Service API: http://localhost:8002/docs

## Development

### Manual Commands
```bash
# Start (or use ./start.sh)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

# Stop (or use ./stop.sh)
docker-compose down

# View logs
docker-compose logs -f
```
