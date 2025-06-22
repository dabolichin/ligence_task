from enum import Enum

from tortoise import fields
from tortoise.models import Model


class AlgorithmType(str, Enum):
    """Enumeration of available modification algorithms."""

    XOR_TRANSFORM = "xor_transform"
    PIXEL_REORDER = "pixel_reorder"
    PIXEL_SHIFT = "pixel_shift"


class Modification(Model):
    id = fields.UUIDField(primary_key=True)
    image = fields.ForeignKeyField(
        "models.Image", related_name="modifications", on_delete=fields.CASCADE
    )
    variant_number = fields.IntField(
        description="Sequential number of this variant (1-100)"
    )
    algorithm_type = fields.CharEnumField(
        AlgorithmType, description="Type of algorithm used for modification"
    )
    instructions = fields.JSONField(
        description="JSON-encoded modification instructions for reversibility"
    )
    storage_path = fields.CharField(
        max_length=500, description="Relative path to stored modified image file"
    )

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "modifications"

    def __str__(self) -> str:
        return (
            f"<Modification(id={self.id}, variant={self.variant_number}, "
            f"algorithm='{self.algorithm_type.value}')>"
        )
