from tortoise import fields
from tortoise.models import Model

from ..services.domain import VerificationStatus


class VerificationResult(Model):
    id = fields.UUIDField(primary_key=True)
    modification_id = fields.UUIDField()
    status = fields.CharEnumField(
        VerificationStatus, default=VerificationStatus.PENDING
    )
    verified_with_hash = fields.BooleanField(default=False)
    verified_with_pixels = fields.BooleanField(default=False)
    is_reversible = fields.BooleanField(null=True)
    error_message = fields.TextField(null=True)

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "verification_results"

    def __str__(self) -> str:
        return f"<VerificationResult(id={self.id}, modification_id={self.modification_id}, status={self.status.value})>"
