from fastapi import APIRouter

router = APIRouter()


# Placeholder endpoints - TBD
@router.get("/modifications/{modification_id}/instructions")
async def get_modification_instructions(modification_id: str):
    return {
        "message": f"Instructions endpoint for {modification_id} - not yet implemented"
    }
