from uuid import UUID

import httpx
from loguru import logger

from ..core.config import Settings
from ..schemas import ModificationInstructionData
from .domain import InstructionRetrievalError


class InstructionRetrievalService:
    def __init__(self, settings: Settings | None = None):
        from ..core.config import get_settings

        self.settings = settings or get_settings()
        self.base_url = self.settings.IMAGE_PROCESSING_SERVICE_URL

    async def get_modification_instructions(
        self, modification_id: UUID
    ) -> ModificationInstructionData:
        url = f"{self.base_url}/internal/modifications/{modification_id}/instructions"

        logger.info(f"Retrieving modification instructions for {modification_id}")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)

                if response.status_code == 404:
                    raise InstructionRetrievalError(
                        f"Modification {modification_id} not found"
                    )

                if response.status_code != 200:
                    raise InstructionRetrievalError(
                        f"HTTP {response.status_code}: {response.text}"
                    )

                data = response.json()

                logger.info(
                    f"Successfully retrieved instructions for modification {modification_id}"
                )

                return ModificationInstructionData(**data)

        except httpx.TimeoutException as e:
            logger.error(
                "Timeout retrieving instructions for {}: {}", modification_id, str(e)
            )
            raise InstructionRetrievalError(f"Request timeout: {str(e)}") from e

        except httpx.RequestError as e:
            logger.error(
                "Network error retrieving instructions for {}: {}",
                modification_id,
                str(e),
            )
            raise InstructionRetrievalError(f"Network error: {str(e)}") from e

        except Exception as e:
            logger.error(
                "Unexpected error retrieving instructions for {}: {}",
                modification_id,
                str(e),
                exc_info=True,
            )
            raise InstructionRetrievalError(f"Unexpected error: {str(e)}") from e
