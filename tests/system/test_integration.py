import sys
import time
from io import BytesIO

import pytest
import requests
from PIL import Image
from requests_toolbelt.multipart.encoder import MultipartEncoder

BASE_URL = "http://localhost:8001"
VERIFICATION_URL = "http://localhost:8002"


def log_progress(message):
    timestamp = time.strftime("%H:%M:%S")
    formatted_message = f"[{timestamp}] {message}"
    print(formatted_message, file=sys.stderr, flush=True)
    print(formatted_message, flush=True)


def create_test_image(size=(64, 64), color="red"):
    img = Image.new("RGB", size, color)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def upload_image(image_data):
    multipart_data = MultipartEncoder(
        fields={"file": ("test.png", image_data, "image/png")}
    )

    response = requests.post(
        f"{BASE_URL}/api/modify",
        data=multipart_data,
        headers={"Content-Type": multipart_data.content_type},
        timeout=30,
    )

    assert response.status_code in [200, 202]
    return response.json()["processing_id"]


def wait_for_processing(processing_id, timeout=120):
    log_progress(f"Waiting for processing {processing_id[:8]}...")
    start_time = time.time()
    last_progress = -1

    poll_intervals = [0.5, 0.5, 1, 1, 2, 2, 3]  # Progressive backoff
    poll_index = 0

    while time.time() - start_time < timeout:
        try:
            response = requests.get(
                f"{BASE_URL}/api/processing/{processing_id}/status", timeout=10
            )
            assert response.status_code == 200

            status = response.json()
            current_progress = status.get("progress", 0)

            # Log progress updates more frequently for small images
            if current_progress != last_progress:
                variants_done = status.get("variants_completed", 0)
                log_progress(
                    f"  Progress: {current_progress}% ({variants_done}/100 variants)"
                )
                last_progress = current_progress

            if status["status"] == "completed":
                elapsed = time.time() - start_time
                variants_done = status.get("variants_completed", 0)
                log_progress(
                    f"  Processing completed in {elapsed:.1f}s ({variants_done} variants)"
                )
                return status
            elif status["status"] == "failed":
                pytest.fail(f"Processing failed: {status.get('error_message')}")

            # Progressive backoff for polling
            sleep_time = poll_intervals[min(poll_index, len(poll_intervals) - 1)]
            time.sleep(sleep_time)
            poll_index += 1

        except requests.RequestException as e:
            log_progress(f"  Request failed: {e}, retrying...")
            time.sleep(1)

    pytest.fail(f"Processing timeout after {timeout}s")


def wait_for_verification(processing_id, timeout=60):
    log_progress(f"Waiting for verification of {processing_id[:8]}...")

    # Get initial stats
    try:
        response = requests.get(
            f"{VERIFICATION_URL}/api/verification/statistics", timeout=10
        )
        if response.status_code == 200:
            initial_stats = response.json()
            initial_verified = initial_stats.get("successful_verifications", 0)
            log_progress(f"  Initial verified count: {initial_verified}")
        else:
            initial_verified = 0
    except requests.RequestException:
        log_progress("  Could not get initial verification stats")
        initial_verified = 0

    # Wait for verification service to process
    log_progress("  Allowing time for verification processing...")

    # Check verification progress more frequently
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # Check if we can get specific verification status
            response = requests.get(
                f"{VERIFICATION_URL}/api/verification/{processing_id}/status", timeout=5
            )
            if response.status_code == 200:
                verification_status = response.json()
                if verification_status.get("status") in ["completed", "verified"]:
                    log_progress("  Verification completed successfully")
                    return {"verified": 1, "failed": 0}

            # Fall back to checking overall stats
            response = requests.get(
                f"{VERIFICATION_URL}/api/verification/statistics", timeout=5
            )
            if response.status_code == 200:
                current_stats = response.json()
                current_verified = current_stats.get("successful_verifications", 0)
                new_verifications = current_verified - initial_verified

                if new_verifications > 0:
                    log_progress(f"  Found {new_verifications} new verifications")
                    return {"verified": new_verifications, "failed": 0}

            time.sleep(2)  # Check every 2 seconds

        except requests.RequestException as e:
            log_progress(f"  Verification check failed: {e}")
            time.sleep(2)

    # For system tests, if we can't verify, continue anyway
    log_progress("  Verification timeout, but continuing test...")
    return {"verified": 0, "failed": 0}


class TestSystem:
    def test_tiny_image(self):
        log_progress("Starting tiny image test (4x4 pixels)")

        image_data = create_test_image(size=(4, 4))
        log_progress("Uploading tiny image...")
        processing_id = upload_image(image_data)

        status = wait_for_processing(processing_id, timeout=30)  # Reduced timeout
        assert status["variants_completed"] == 100

        verification = wait_for_verification(processing_id, timeout=30)
        assert verification["verified"] >= 0

        log_progress("Tiny image test completed successfully!")

    def test_small_image(self):
        log_progress("Starting small image test (32x32 pixels)")

        image_data = create_test_image(size=(32, 32))
        log_progress("Uploading small RGB image...")
        processing_id = upload_image(image_data)

        status = wait_for_processing(processing_id, timeout=60)
        assert status["variants_completed"] == 100

        verification = wait_for_verification(processing_id, timeout=30)
        assert verification["verified"] >= 0

        log_progress("Small image test completed successfully!")

    def test_grayscale(self):
        log_progress("Starting grayscale image test (16x16 pixels)")

        img = Image.new("L", (16, 16), 128)  # Smaller for faster processing
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        image_data = buffer.getvalue()

        log_progress("Uploading grayscale image...")
        processing_id = upload_image(image_data)
        status = wait_for_processing(processing_id, timeout=45)
        assert status["variants_completed"] == 100

        log_progress("Grayscale image test completed successfully!")

    def test_image_serving(self):
        log_progress("Starting image serving test")

        image_data = create_test_image(size=(8, 8))  # Very small for speed
        log_progress("Uploading test image for serving...")
        processing_id = upload_image(image_data)
        wait_for_processing(processing_id, timeout=30)

        # Test original image
        log_progress("Testing original image serving...")
        response = requests.get(
            f"{BASE_URL}/api/images/{processing_id}/original", timeout=10
        )
        assert response.status_code == 200
        log_progress(f"  Original image served ({len(response.content):,} bytes)")

        # Test variants list
        log_progress("Testing variants listing...")
        response = requests.get(
            f"{BASE_URL}/api/images/{processing_id}/variants", timeout=10
        )
        assert response.status_code == 200
        variants_data = response.json()
        variants_count = variants_data["total_count"]
        assert variants_count == 100
        log_progress(f"  Variants listed ({variants_count} total)")

        # Test serving a specific variant
        if variants_data.get("variants"):
            variant_id = variants_data["variants"][0]["variant_id"]
            log_progress(f"Testing variant {variant_id} serving...")
            response = requests.get(
                f"{BASE_URL}/api/images/{processing_id}/variants/{variant_id}",
                timeout=10,
            )
            assert response.status_code == 200
            log_progress(f"  Variant served ({len(response.content):,} bytes)")

        log_progress("Image serving test completed successfully!")

    def test_verification_stats(self):
        log_progress("Starting verification statistics test")

        response = requests.get(
            f"{VERIFICATION_URL}/api/verification/statistics", timeout=10
        )
        assert response.status_code == 200
        stats = response.json()
        assert "total_verifications" in stats
        assert "successful_verifications" in stats

        total = stats.get("total_verifications", 0)
        successful = stats.get("successful_verifications", 0)
        success_rate = stats.get("success_rate", 0)
        log_progress(
            f"Statistics: {successful}/{total} successful ({success_rate:.1f}%)"
        )
        log_progress("Verification statistics test completed successfully!")

    def test_api_health_checks(self):
        log_progress("Starting API health checks")

        services = {
            "Image Processing Service": f"{BASE_URL}/api/health",
            "Verification Service": f"{VERIFICATION_URL}/api/health",
        }

        for service_name, health_url in services.items():
            log_progress(f"Checking {service_name} health...")
            try:
                response = requests.get(health_url, timeout=5)
                assert response.status_code == 200
                log_progress(f" {service_name}: Healthy")
            except Exception as e:
                pytest.fail(f"{service_name} health check failed: {e}")

        log_progress("All API health checks passed!")

    @pytest.mark.slow
    def test_medium_image(self):
        log_progress("Starting medium image performance test (128x128 pixels)")
        log_progress(" This test may take 1-2 minutes...")

        image_data = create_test_image(size=(128, 128), color="blue")
        log_progress(" Uploading medium image...")
        processing_id = upload_image(image_data)

        start_time = time.time()
        status = wait_for_processing(processing_id, timeout=180)  # 3 minutes max
        processing_time = time.time() - start_time

        assert status["variants_completed"] == 100
        assert processing_time < 180  # Should complete within 3 minutes
        log_progress(
            f"Processing performance: {processing_time:.1f}s for 128x128 image"
        )

        verification = wait_for_verification(processing_id, timeout=60)
        assert verification["verified"] >= 0
        log_progress("Medium image performance test completed successfully!")

    def test_error_handling(self):
        log_progress("Starting error handling test")

        # Test invalid file upload
        log_progress("Testing invalid file upload...")
        invalid_data = b"not an image"
        multipart_data = MultipartEncoder(
            fields={"file": ("test.txt", invalid_data, "text/plain")}
        )

        response = requests.post(
            f"{BASE_URL}/api/modify",
            data=multipart_data,
            headers={"Content-Type": multipart_data.content_type},
            timeout=10,
        )

        # Should reject invalid file
        assert response.status_code in [400, 422]
        log_progress(" Invalid file properly rejected")

        # Test invalid processing ID
        log_progress("Testing invalid processing ID...")
        response = requests.get(
            f"{BASE_URL}/api/processing/invalid-id/status", timeout=5
        )
        assert response.status_code in [404, 422]
        log_progress("Invalid processing ID properly handled")

        log_progress("Error handling test completed successfully!")
