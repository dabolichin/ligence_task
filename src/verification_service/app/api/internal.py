from typing import Dict

from fastapi import APIRouter
from loguru import logger

router = APIRouter()


@router.post("/verify")
async def receive_verification_request(
    verification_request: Dict,
) -> Dict:
    """Receive verification request from Image Processing Service."""
    logger.info(f"Received verification request: {verification_request}")

    return {
        "status": "accepted",
        "verification_id": "temp_verification_id",
        "message": "Verification request received - not implemented yet",
    }
