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
    async def test_image_creation_with_all_fields(self):
        image = await Image.create(
            original_filename="test.png",
            file_size=2048,
            width=1024,
            height=768,
            format="PNG",
            storage_path="/storage/images/test.png",
        )

        assert image.id is not None
        assert image.original_filename == "test.png"
        assert image.file_size == 2048
        assert image.width == 1024
        assert image.height == 768
        assert image.format == "PNG"
        assert image.storage_path == "/storage/images/test.png"
        assert image.created_at is not None
        assert image.updated_at is not None

        await image.delete()

    async def test_image_creation_minimal_fields(self):
        image = await Image.create(
            original_filename="minimal.jpg",
            file_size=512,
            width=None,
            height=None,
            format=None,
            storage_path="/storage/images/minimal.jpg",
        )

        assert image.id is not None
        assert image.original_filename == "minimal.jpg"
        assert image.file_size == 512
        assert image.width is None
        assert image.height is None
        assert image.format is None
        assert image.created_at is not None
        assert image.updated_at is not None

        await image.delete()


class TestModificationModel:
    async def test_modification_creation(self, sample_image):
        instructions = {"xor_key": 42, "positions": [[100, 150], [200, 250]]}

        modification = await Modification.create(
            image=sample_image,
            variant_number=1,
            algorithm_type=AlgorithmType.XOR_TRANSFORM,
            instructions=instructions,
            storage_path="/storage/variants/test_variant_1.jpg",
        )

        assert modification.id is not None
        assert modification.image_id == sample_image.id
        assert modification.variant_number == 1
        assert modification.algorithm_type == AlgorithmType.XOR_TRANSFORM
        assert modification.instructions == instructions
        assert modification.instructions["xor_key"] == 42
        assert modification.instructions["positions"] == [[100, 150], [200, 250]]
        assert modification.created_at is not None
        assert modification.updated_at is not None

        await modification.delete()

    async def test_multiple_modifications_per_image(self, sample_image):
        variant_numbers = [1, 2, 3]
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

        assert len(image_with_mods.modifications) == 3
        retrieved_variants = [
            mod.variant_number for mod in image_with_mods.modifications
        ]
        assert sorted(retrieved_variants) == [1, 2, 3]

        for mod in modifications:
            await mod.delete()

    async def test_cascade_deletion(self):
        image = await Image.create(
            original_filename="cascade_test.jpg",
            file_size=1024,
            storage_path="/storage/images/cascade_test.jpg",
        )

        modification_ids = []
        for i in range(3):
            instructions = {"xor_key": i + 1, "positions": [[i, i + 1]]}
            mod = await Modification.create(
                image=image,
                variant_number=i + 1,
                algorithm_type=AlgorithmType.XOR_TRANSFORM,
                instructions=instructions,
                storage_path=f"/storage/variants/cascade_{i}.jpg",
            )
            modification_ids.append(mod.id)

        assert await Modification.filter(image=image).count() == 3

        await image.delete()

        for mod_id in modification_ids:
            assert await Modification.filter(id=mod_id).count() == 0
