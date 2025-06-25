from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from uuid import UUID


class VerificationStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class ComparisonMethod(Enum):
    HASH_ONLY = "hash_only"
    PIXEL_ONLY = "pixel_only"
    BOTH = "both"


@dataclass(frozen=True)
class ComparisonResult:
    hash_match: bool | None
    pixel_match: bool | None
    original_hash: str | None
    reversed_hash: str | None
    method_used: str

    def __str__(self) -> str:
        return (
            f"ComparisonResult(hash_match={self.hash_match}, "
            f"pixel_match={self.pixel_match}, method_used={self.method_used})"
        )

    @property
    def is_successful(self) -> bool:
        if self.method_used == ComparisonMethod.HASH_ONLY.value:
            return self.hash_match is True
        elif self.method_used == ComparisonMethod.PIXEL_ONLY.value:
            return self.pixel_match is True
        else:  # BOTH
            return self.hash_match is True and self.pixel_match is True


@dataclass(frozen=True)
class VerificationOutcome:
    is_reversible: bool
    verified_with_hash: bool
    verified_with_pixels: bool

    @property
    def is_successful(self) -> bool:
        return (
            self.is_reversible and self.verified_with_hash and self.verified_with_pixels
        )


@dataclass
class VerificationResult:
    modification_id: UUID
    status: VerificationStatus
    outcome: VerificationOutcome | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    def __post_init__(self):
        if self.started_at is None:
            self.started_at = datetime.utcnow()

    @property
    def is_complete(self) -> bool:
        return self.status == VerificationStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        return self.status == VerificationStatus.FAILED

    @property
    def is_successful(self) -> bool:
        return (
            self.is_complete and self.outcome is not None and self.outcome.is_successful
        )

    @property
    def duration_seconds(self) -> float | None:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


@dataclass
class VerificationStatistics:
    total: int
    completed: int
    pending: int
    successful: int
    failed: int
    success_rate: float

    @classmethod
    def create_empty(cls) -> "VerificationStatistics":
        return cls(
            total=0, completed=0, pending=0, successful=0, failed=0, success_rate=0.0
        )

    @property
    def failure_rate(self) -> float:
        return 100.0 - self.success_rate if self.completed > 0 else 0.0


@dataclass
class VerificationErrorInfo:
    modification_id: UUID
    stage: str  # "retrieval", "parsing", "reversal", "comparison", etc.
    error_type: str
    error_message: str
    occurred_at: datetime
    recoverable: bool = False

    def __post_init__(self):
        if self.occurred_at is None:
            self.occurred_at = datetime.utcnow()


class VerificationError(Exception):
    pass


class InstructionRetrievalError(VerificationError):
    pass


class InstructionParseError(VerificationError):
    pass


class ImageReversalError(VerificationError):
    pass


class ComparisonError(VerificationError):
    pass
