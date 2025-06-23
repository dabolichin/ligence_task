import pytest

from src.image_processing_service.app.api.public import _get_media_type_from_path


class TestHTTPHelpers:
    @pytest.mark.parametrize(
        "file_path,expected_media_type",
        [
            ("/path/to/image.jpg", "image/jpeg"),
            ("/path/to/image.jpeg", "image/jpeg"),
            ("/path/to/image.png", "image/png"),
            ("/path/to/image.bmp", "image/bmp"),
            ("/path/to/image.unknown", "application/octet-stream"),
            ("/path/to/image", "application/octet-stream"),
            ("image.JPG", "image/jpeg"),
            ("image.PNG", "image/png"),
            # Edge cases
            ("", "application/octet-stream"),
            (".jpg", "image/jpeg"),
            ("my.image.file.png", "image/png"),
            ("/path/with spaces/image.bmp", "image/bmp"),
        ],
    )
    def test_get_media_type_from_path(self, file_path, expected_media_type):
        result = _get_media_type_from_path(file_path)
        assert result == expected_media_type, f"Failed for {file_path}"
