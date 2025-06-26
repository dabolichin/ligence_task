from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).parent

app = FastAPI(
    title="Reversible Image Modification System - Web Interface",
    description="Frontend interface for image processing and verification",
    version="1.0.0",
)

# Serve React build files
app.mount(
    "/assets", StaticFiles(directory=str(BASE_DIR / "dist" / "assets")), name="assets"
)


@app.get("/", response_class=HTMLResponse)
async def home():
    """Serve the React app."""
    return FileResponse(str(BASE_DIR / "dist" / "index.html"))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "web_interface"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
