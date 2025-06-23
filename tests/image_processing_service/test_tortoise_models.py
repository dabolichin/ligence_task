import pytest

from src.image_processing_service.app.models import AlgorithmType, Image, Modification


@pytest.fixture
async def sample_image():
    image = await Image.create(
        original_filename="test.jpg",
        file_size=1024,
        width=800,
        height=600,
        format="JPEG",
        storage_path="/storage/images/test.jpg",
    )
    return image


class TestImageModel:
    @pytest.mark.parametrize(
        "filename,file_size,width,height,format",
        [
            # Test with all fields
            ("test.png", 2048, 1024, 768, "PNG"),
            ("image.jpg", 1024, 800, 600, "JPEG"),
            # Test with optional fields as None
            ("minimal.jpg", 512, None, None, None),
            ("no_dims.png", 1024, None, None, "PNG"),
            ("no_format.jpg", 2048, 800, 600, None),
        ],
    )
    async def test_image_creation(self, filename, file_size, width, height, format):
        image = await Image.create(
            original_filename=filename,
            file_size=file_size,
            width=width,
            height=height,
            format=format,
            storage_path=f"/storage/images/{filename}",
        )

        assert image.id is not None
        assert image.original_filename == filename
        assert image.file_size == file_size
        assert image.width == width
        assert image.height == height
        assert image.format == format
        assert image.storage_path == f"/storage/images/{filename}"
        assert image.created_at is not None
        assert image.updated_at is not None

        # Clean up
        await image.delete()


class TestModificationModel:
    """Test suite for Modification model."""

    @pytest.mark.parametrize(
        "variant_number,xor_key,positions",
        [
            (1, 42, [[100, 150], [200, 250]]),
            (50, 128, [[0, 0], [10, 10], [20, 20]]),
            (100, 255, [[50, 75]]),
        ],
    )
    async def test_modification_creation(
        self, sample_image, variant_number, xor_key, positions
    ):
        """Test modification creation with XOR algorithm instructions."""
        instructions = {"xor_key": xor_key, "positions": positions}

        modification = await Modification.create(
            image=sample_image,
            variant_number=variant_number,
            algorithm_type=AlgorithmType.XOR_TRANSFORM,
            instructions=instructions,
            storage_path=f"/storage/variants/test_variant_{variant_number}.jpg",
        )

        assert modification.id is not None
        assert modification.image_id == sample_image.id
        assert modification.variant_number == variant_number
        assert modification.algorithm_type == AlgorithmType.XOR_TRANSFORM
        assert modification.instructions == instructions
        assert modification.instructions["xor_key"] == xor_key
        assert modification.instructions["positions"] == positions
        assert modification.created_at is not None
        assert modification.updated_at is not None

        await modification.delete()

    @pytest.mark.parametrize(
        "variant_numbers",
        [
            [1, 2, 3],
            [1, 50, 100],
            [10, 20, 30, 40, 50],
        ],
    )
    async def test_multiple_modifications_per_image(
        self, sample_image, variant_numbers
    ):
        modifications = []

        for variant_num in variant_numbers:
            instructions = {
                "xor_key": variant_num * 10,
                "positions": [[variant_num, variant_num + 1]],
            }
            mod = await Modification.create(
                image=sample_image,
                variant_number=variant_num,
                algorithm_type=AlgorithmType.XOR_TRANSFORM,
                instructions=instructions,
                storage_path=f"/storage/variants/multi_test_{variant_num}.jpg",
            )
            modifications.append(mod)

        image_with_mods = await Image.get(id=sample_image.id).prefetch_related(
            "modifications"
        )

        assert len(image_with_mods.modifications) == len(variant_numbers)
        retrieved_variants = [
            mod.variant_number for mod in image_with_mods.modifications
        ]
        assert sorted(retrieved_variants) == sorted(variant_numbers)

        for mod in modifications:
            await mod.delete()


class TestModelRelationships:
    @pytest.mark.parametrize("num_modifications", [1, 3, 5])
    async def test_cascade_deletion(self, num_modifications):
        image = await Image.create(
            original_filename="cascade_test.jpg",
            file_size=1024,
            storage_path="/storage/images/cascade_test.jpg",
        )

        modification_ids = []
        for i in range(num_modifications):
            instructions = {"xor_key": i + 1, "positions": [[i, i + 1]]}
            mod = await Modification.create(
                image=image,
                variant_number=i + 1,
                algorithm_type=AlgorithmType.XOR_TRANSFORM,
                instructions=instructions,
                storage_path=f"/storage/variants/cascade_{i}.jpg",
            )
            modification_ids.append(mod.id)

        assert await Modification.filter(image=image).count() == num_modifications

        await image.delete()

        for mod_id in modification_ids:
            assert await Modification.filter(id=mod_id).count() == 0
