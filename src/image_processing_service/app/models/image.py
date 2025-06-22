from tortoise import fields
from tortoise.models import Model


class Image(Model):
    id = fields.UUIDField(primary_key=True)
    original_filename = fields.CharField(
        max_length=255, description="Original filename as uploaded by user"
    )
    file_size = fields.IntField(description="File size in bytes")
    width = fields.IntField(null=True, description="Image width in pixels")
    height = fields.IntField(null=True, description="Image height in pixels")
    format = fields.CharField(
        max_length=10, null=True, description="Image format (JPEG, PNG, BMP, etc.)"
    )
    storage_path = fields.CharField(
        max_length=500, description="Relative path to stored image file"
    )

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    modifications = fields.ReverseRelation["Modification"]

    class Meta:
        table = "images"

    def __str__(self) -> str:
        return f"<Image(id={self.id}, filename='{self.original_filename}', size={self.file_size} bytes)>"
