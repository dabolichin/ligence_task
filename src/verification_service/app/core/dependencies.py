from functools import lru_cache

from image_modification_algorithms import ModificationEngine

from ..core.config import Settings, get_settings
from ..services.image_comparison import ImageComparisonService
from ..services.image_reversal import ImageReversalService
from ..services.instruction_retrieval import InstructionRetrievalService
from ..services.verification_history import VerificationHistoryService
from ..services.verification_orchestrator import VerificationOrchestrator
from ..services.verification_persistence import VerificationPersistence


@lru_cache()
def get_settings_dependency() -> Settings:
    return get_settings()


@lru_cache()
def get_modification_engine() -> ModificationEngine:
    return ModificationEngine()


@lru_cache()
def get_instruction_retrieval_service() -> InstructionRetrievalService:
    settings = get_settings()
    return InstructionRetrievalService(settings=settings)


@lru_cache()
def get_image_comparison_service() -> ImageComparisonService:
    return ImageComparisonService()


def get_image_reversal_service() -> ImageReversalService:
    return ImageReversalService(image_comparison_service=get_image_comparison_service())


@lru_cache()
def get_verification_persistence() -> VerificationPersistence:
    return VerificationPersistence()


def get_verification_orchestrator() -> VerificationOrchestrator:
    return VerificationOrchestrator(
        instruction_retrieval_service=get_instruction_retrieval_service(),
        modification_engine=get_modification_engine(),
        image_reversal_service=get_image_reversal_service(),
        verification_persistence=get_verification_persistence(),
    )


@lru_cache()
def get_verification_history_service() -> VerificationHistoryService:
    return VerificationHistoryService()
