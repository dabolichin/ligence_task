from fastapi import APIRouter

router = APIRouter()


# Placeholder endpoints - TBD
@router.post("/modify")
async def modify_image():
    return {"message": "Not yet implemented"}


@router.get("/processing/{processing_id}/status")
async def get_processing_status(processing_id: str):
    return {"message": "Not yet implemented"}


@router.get("/modifications/{modification_id}")
async def get_modification_details(modification_id: str):
    return {"message": "Not yet implemented"}


@router.get("/images/{image_id}/original")
async def serve_original_image(image_id: str):
    return {"message": "Not yet implemented"}


@router.get("/images/{image_id}/variants/{variant_id}")
async def serve_variant_image(image_id: str, variant_id: str):
    return {"message": "Not yet implemented"}


@router.get("/images/{image_id}/variants")
async def list_image_variants(image_id: str):
    return {"message": "Not yet implemented"}
