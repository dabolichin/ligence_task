from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from loguru import logger

from ..core.dependencies import get_file_storage, get_processing_orchestrator
from ..models import Image as ImageModel
from ..models import Modification
from ..schemas import (
    ImageListResponse,
    ImageSummary,
    ImageUploadResponse,
    ModificationDetails,
    ProcessingStatus,
    VariantInfo,
    VariantListResponse,
)
from ..services.file_storage import FileStorageService
from ..services.processing_orchestrator import ProcessingOrchestrator

router = APIRouter()


@router.post("/modify", response_model=ImageUploadResponse)
async def modify_image(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    orchestrator: ProcessingOrchestrator = Depends(get_processing_orchestrator),
):
    """
    Upload an image file and start processing to generate 100 variants.

    Args:
        file: Image file to process (JPEG, PNG, BMP supported)

    Returns:
        ImageUploadResponse with processing ID and file information

    Raises:
        HTTPException: For invalid files or processing errors
    """
    logger.info(f"Received image upload request: {file.filename}")

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    MAX_FILE_SIZE = 100 * 1024 * 1024

    try:
        file_data = await file.read()

        if len(file_data) == 0:
            raise HTTPException(status_code=400, detail="Empty file provided")

        if len(file_data) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)}MB",
            )

        image_id, processing_info = await orchestrator.start_image_processing(
            file_data, file.filename
        )

        # Add background task for variant generation
        background_tasks.add_task(orchestrator.process_variants_background, image_id)

        logger.info(f"Started processing image {file.filename} with ID {image_id}")

        return ImageUploadResponse(
            processing_id=UUID(image_id),
            message=processing_info["message"],
            original_filename=processing_info["original_filename"],
            file_size=processing_info["file_size"],
        )

    except ValueError as e:
        logger.warning(f"Validation error for file {file.filename}: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except IOError as e:
        logger.error(f"File I/O error for {file.filename}: {e}")
        raise HTTPException(status_code=500, detail="Failed to process file")

    except Exception as e:
        logger.error(f"Unexpected error processing {file.filename}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/processing/{processing_id}/status", response_model=ProcessingStatus)
async def get_processing_status(
    processing_id: UUID,
    orchestrator: ProcessingOrchestrator = Depends(get_processing_orchestrator),
):
    """
    Get the current processing status for an image.

    Args:
        processing_id: UUID of the processing task

    Returns:
        ProcessingStatus with current progress and status

    Raises:
        HTTPException: If processing ID not found
    """
    logger.info(f"Getting processing status for {processing_id}")

    try:
        status_result = await orchestrator.get_processing_status(str(processing_id))

        if not status_result:
            raise HTTPException(
                status_code=404, detail=f"Processing task {processing_id} not found"
            )

        return ProcessingStatus(
            processing_id=UUID(status_result.processing_id),
            status=status_result.status,
            progress=status_result.progress,
            variants_completed=status_result.variants_completed,
            total_variants=status_result.total_variants,
            created_at=status_result.created_at,
            completed_at=status_result.completed_at,
            error_message=status_result.error_message,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting processing status for {processing_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/modifications/{modification_id}", response_model=ModificationDetails)
async def get_modification_details(
    modification_id: UUID,
    orchestrator: ProcessingOrchestrator = Depends(get_processing_orchestrator),
):
    """
    Get detailed information about an image and its modifications.

    Args:
        modification_id: UUID of the image (same as processing_id)

    Returns:
        ModificationDetails with image and processing information

    Raises:
        HTTPException: If image not found
    """
    logger.info(f"Getting modification details for {modification_id}")

    try:
        image_with_variants = await orchestrator.get_modification_details(
            str(modification_id)
        )

        if not image_with_variants:
            raise HTTPException(
                status_code=404, detail=f"Image {modification_id} not found"
            )

        return ModificationDetails(
            image_id=UUID(str(image_with_variants.image.id)),
            original_filename=image_with_variants.image.original_filename,
            file_size=image_with_variants.image.file_size,
            width=image_with_variants.image.width,
            height=image_with_variants.image.height,
            format=image_with_variants.image.format,
            variants_count=image_with_variants.variants_count,
            created_at=image_with_variants.image.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting modification details for {modification_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/images/{image_id}/original")
async def serve_original_image(
    image_id: UUID,
    file_storage: FileStorageService = Depends(get_file_storage),
):
    """
    Serve the original image file.

    Args:
        image_id: UUID of the image

    Returns:
        FileResponse with the original image

    Raises:
        HTTPException: If image not found or file missing
    """
    logger.info(f"Serving original image for {image_id}")

    try:
        image_record = await ImageModel.get(id=str(image_id))

        if not await file_storage.file_exists(image_record.storage_path):
            raise HTTPException(
                status_code=404, detail="Original image file not found on disk"
            )

        return FileResponse(
            path=image_record.storage_path,
            media_type=_get_media_type_from_path(image_record.storage_path),
            filename=image_record.original_filename,
        )

    except Exception as e:
        if "DoesNotExist" in str(type(e)):
            logger.warning(f"Image {image_id} not found")
            raise HTTPException(status_code=404, detail=f"Image {image_id} not found")
        logger.error(f"Error serving original image for {image_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/images/{image_id}/variants", response_model=VariantListResponse)
async def list_image_variants(
    image_id: UUID,
    orchestrator: ProcessingOrchestrator = Depends(get_processing_orchestrator),
):
    """
    List all variants for an image.

    Args:
        image_id: UUID of the image

    Returns:
        VariantListResponse with list of all variants

    Raises:
        HTTPException: If image not found
    """
    logger.info(f"Listing variants for image {image_id}")

    try:
        modifications = await orchestrator.get_image_variants(str(image_id))

        if not modifications:
            raise HTTPException(status_code=404, detail=f"Image {image_id} not found")

        variants = [
            VariantInfo(
                variant_id=UUID(str(mod.id)),
                variant_number=mod.variant_number,
                algorithm_type=mod.algorithm_type.value,
                num_modifications=len(mod.instructions.get("operations", [])),
                storage_path=mod.storage_path,
                created_at=mod.created_at,
            )
            for mod in modifications
        ]

        return VariantListResponse(
            image_id=image_id,
            variants=variants,
            total_count=len(variants),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing variants for image {image_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/images/{image_id}/variants/{variant_id}")
async def serve_variant_image(
    image_id: UUID,
    variant_id: UUID,
    file_storage: FileStorageService = Depends(get_file_storage),
):
    """
    Serve a specific variant image file.

    Args:
        image_id: UUID of the image
        variant_id: UUID of the variant (modification ID)

    Returns:
        FileResponse with the variant image

    Raises:
        HTTPException: If image or variant not found
    """
    logger.info(f"Serving variant {variant_id} for image {image_id}")

    try:
        modification = await Modification.get(
            id=str(variant_id), image_id=str(image_id)
        )
        image_record = await ImageModel.get(id=str(image_id))

        if not await file_storage.file_exists(modification.storage_path):
            raise HTTPException(
                status_code=404, detail="Variant image file not found on disk"
            )

        variant_filename = file_storage.generate_variant_filename(
            image_record.original_filename, modification.variant_number
        )

        return FileResponse(
            path=modification.storage_path,
            media_type=_get_media_type_from_path(modification.storage_path),
            filename=variant_filename,
        )

    except Exception as e:
        if "DoesNotExist" in str(type(e)):
            logger.warning(f"Variant {variant_id} not found for image {image_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Variant {variant_id} not found for image {image_id}",
            )
        logger.error(f"Error serving variant {variant_id} for image {image_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/images", response_model=ImageListResponse)
async def list_images(
    limit: int = 50,
    offset: int = 0,
    orchestrator: ProcessingOrchestrator = Depends(get_processing_orchestrator),
):
    """
    List all processed images with their status.

    Args:
        limit: Maximum number of images to return (default 50)
        offset: Number of images to skip (default 0)

    Returns:
        ImageListResponse with list of images and metadata
    """
    logger.info(f"Listing images with limit={limit}, offset={offset}")

    try:
        images = (
            await ImageModel.all()
            .prefetch_related("modifications")
            .order_by("-created_at")
            .offset(offset)
            .limit(limit)
        )
        total_count = await ImageModel.all().count()

        image_summaries = []
        for image in images:
            variants_count = len(image.modifications)

            if variants_count == 0:
                status = "processing"
            elif variants_count < 100:
                status = "processing"
            else:
                status = "completed"

            image_summaries.append(
                ImageSummary(
                    image_id=image.id,
                    original_filename=image.original_filename,
                    file_size=image.file_size,
                    format=image.format or "unknown",
                    variants_count=variants_count,
                    created_at=image.created_at,
                    status=status,
                )
            )

        return ImageListResponse(
            images=image_summaries,
            total_count=total_count,
        )

    except Exception as e:
        logger.error(f"Error listing images: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "image-processing"}


def _get_media_type_from_path(file_path: str) -> str:
    if not file_path:
        return "application/octet-stream"

    last_dot_index = file_path.rfind(".")
    if last_dot_index == -1:
        return "application/octet-stream"

    extension = file_path[last_dot_index:].lower()

    media_type_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".bmp": "image/bmp",
    }
    return media_type_map.get(extension, "application/octet-stream")
