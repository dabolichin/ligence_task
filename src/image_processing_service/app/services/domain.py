from dataclasses import dataclass
from datetime import datetime

from ..models import Image


@dataclass
class ImageWithVariants:
    image: Image
    variants_count: int


@dataclass
class ProcessingResult:
    processing_id: str
    status: str  # "processing", "completed", "failed"
    progress: int  # 0-100
    variants_completed: int
    total_variants: int
    created_at: datetime
    completed_at: datetime | None = None
    error_message: str | None = None

    @property
    def is_complete(self) -> bool:
        return self.status == "completed"

    @property
    def is_failed(self) -> bool:
        return self.status == "failed"

    @property
    def progress_percentage(self) -> float:
        if self.total_variants == 0:
            return 0.0
        return (self.variants_completed / self.total_variants) * 100.0


@dataclass
class ProcessingRequest:
    file_data: bytes
    original_filename: str
    content_type: str | None = None

    @property
    def file_size_bytes(self) -> int:
        return len(self.file_data)


@dataclass
class ProcessingError:
    processing_id: str
    error_type: str
    error_message: str
    occurred_at: datetime
    stage: str  # "upload", "variant_generation", "storage", etc.
    recoverable: bool = False
