import io
from pathlib import Path

from PIL import Image


class SharedImageFixtures:
    @classmethod
    def get_assets_dir(cls) -> Path:
        return Path(__file__).parent / "assets"

    @classmethod
    def load_tiny_image(cls) -> tuple[bytes, str]:
        assets_dir = cls.get_assets_dir()
        image_path = assets_dir / "tiny_2x2.png"

        if image_path.exists():
            return image_path.read_bytes(), "tiny_2x2.png"
        else:
            image = Image.new("RGB", (2, 2))
            image.putpixel((0, 0), (255, 0, 0))  # Red
            image.putpixel((1, 1), (0, 255, 0))  # Green
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            return buffer.getvalue(), "generated_tiny.png"

    @classmethod
    def load_small_rgb_image(cls) -> tuple[bytes, str]:
        assets_dir = cls.get_assets_dir()
        image_path = assets_dir / "small_red.jpg"

        if image_path.exists():
            return image_path.read_bytes(), "small_red.jpg"
        else:
            image = Image.new("RGB", (10, 10), color=(255, 0, 0))
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG")
            return buffer.getvalue(), "generated_small_rgb.jpg"

    @classmethod
    def load_small_grayscale_image(cls) -> tuple[bytes, str]:
        assets_dir = cls.get_assets_dir()
        image_path = assets_dir / "small_gray.png"

        if image_path.exists():
            return image_path.read_bytes(), "small_gray.png"
        else:
            image = Image.new("L", (10, 10), color=128)
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            return buffer.getvalue(), "generated_small_gray.png"

    @classmethod
    def load_pattern_image(cls) -> tuple[bytes, str]:
        assets_dir = cls.get_assets_dir()
        image_path = assets_dir / "pattern_50x50.jpg"

        if image_path.exists():
            return image_path.read_bytes(), "pattern_50x50.jpg"
        else:
            image = Image.new("RGB", (50, 50))
            for x in range(50):
                for y in range(50):
                    if (x + y) % 10 < 5:
                        image.putpixel((x, y), (255, 0, 0))
                    else:
                        image.putpixel((x, y), (0, 0, 255))
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG")
            return buffer.getvalue(), "generated_pattern.jpg"

    @classmethod
    def create_temp_image_file(
        cls, base_path: Path, image_data: bytes, filename: str
    ) -> Path:
        base_path.mkdir(parents=True, exist_ok=True)
        temp_file = base_path / filename
        temp_file.write_bytes(image_data)
        return temp_file

    @classmethod
    def create_test_image_with_known_pixels(
        cls, width: int = 10, height: int = 10
    ) -> tuple[bytes, str]:
        image = Image.new("RGB", (width, height))

        for x in range(width):
            for y in range(height):
                r = (x * 25) % 256
                g = (y * 25) % 256
                b = ((x + y) * 25) % 256
                image.putpixel((x, y), (r, g, b))

        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue(), f"test_known_pixels_{width}x{height}.png"
