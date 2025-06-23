#!/usr/bin/env python3

from pathlib import Path

from PIL import Image, ImageDraw


def create_test_images():
    """Create small test images for integration testing."""

    script_dir = Path(__file__).parent

    red_image = Image.new("RGB", (10, 10), color="red")
    red_image.save(script_dir / "small_red.jpg", "JPEG", quality=95)

    blue_image = Image.new("RGB", (10, 10), color="blue")
    blue_image.save(script_dir / "small_blue.png", "PNG")

    green_image = Image.new("RGB", (10, 10), color="green")
    green_image.save(script_dir / "small_green.bmp", "BMP")

    pattern_image = Image.new("RGB", (50, 50), color="white")
    draw = ImageDraw.Draw(pattern_image)
    # Create a simple checkerboard pattern
    for x in range(0, 50, 10):
        for y in range(0, 50, 10):
            if (x // 10 + y // 10) % 2 == 0:
                draw.rectangle([x, y, x + 10, y + 10], fill="black")
    pattern_image.save(script_dir / "pattern_50x50.jpg", "JPEG", quality=95)

    # Small grayscale (10x10) - PNG
    gray_image = Image.new("L", (10, 10), color=128)  # Medium gray
    gray_image.save(script_dir / "small_gray.png", "PNG")

    # Medium grayscale with gradient (30x30) - JPEG
    gradient_image = Image.new("L", (30, 30))
    pixels = []
    for y in range(30):
        for x in range(30):
            # Create a diagonal gradient
            intensity = int((x + y) * 255 / 58)  # 58 = 29+29
            pixels.append(intensity)
    gradient_image.putdata(pixels)
    gradient_image.save(script_dir / "gradient_30x30.jpg", "JPEG", quality=95)

    # Very small image (2x2) - PNG
    tiny_image = Image.new("RGB", (2, 2))
    tiny_image.putpixel((0, 0), (255, 0, 0))  # Red
    tiny_image.putpixel((1, 0), (0, 255, 0))  # Green
    tiny_image.putpixel((0, 1), (0, 0, 255))  # Blue
    tiny_image.putpixel((1, 1), (255, 255, 0))  # Yellow
    tiny_image.save(script_dir / "tiny_2x2.png", "PNG")

    # Rectangular image (20x10) - JPEG
    rect_image = Image.new("RGB", (20, 10), color="purple")
    rect_image.save(script_dir / "rect_20x10.jpg", "JPEG", quality=95)

    # A slightly larger test image for performance tests (100x100)
    large_pattern = Image.new("RGB", (100, 100), color="white")
    draw = ImageDraw.Draw(large_pattern)

    colors = ["red", "green", "blue", "yellow", "magenta"]
    for i in range(5):
        x1, y1 = 10 + i * 10, 10 + i * 10
        x2, y2 = 90 - i * 10, 90 - i * 10
        draw.rectangle([x1, y1, x2, y2], outline=colors[i], width=2)

    large_pattern.save(script_dir / "test_100x100.png", "PNG")

    print("Created test images:")
    for image_file in script_dir.glob("*.jpg"):
        size = image_file.stat().st_size
        print(f"  {image_file.name}: {size} bytes")
    for image_file in script_dir.glob("*.png"):
        size = image_file.stat().st_size
        print(f"  {image_file.name}: {size} bytes")
    for image_file in script_dir.glob("*.bmp"):
        size = image_file.stat().st_size
        print(f"  {image_file.name}: {size} bytes")


if __name__ == "__main__":
    create_test_images()
