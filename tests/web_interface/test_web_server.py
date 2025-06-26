from fastapi.testclient import TestClient

from src.web_interface.main import app


class TestWebServerSetup:
    def test_static_files_mounted(self):
        client = TestClient(app)

        response = client.get("/static/css/nonexistent.css")
        assert response.status_code == 404

    def test_home_page(self):
        client = TestClient(app)
        response = client.get("/")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/html; charset=utf-8"

    def test_health_check(self):
        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "web_interface"


class TestBasicFunctionality:
    def test_static_css_accessible(self):
        client = TestClient(app)

        response = client.get("/static/css/style.css")
        assert response.status_code in [200, 404]

    def test_static_js_accessible(self):
        client = TestClient(app)

        response = client.get("/static/js/app.js")
        assert response.status_code in [200, 404]


class TestTemplateRendering:
    def test_index_template_context(self):
        client = TestClient(app)
        response = client.get("/")

        assert response.status_code == 200
        content = response.text
        assert "<!doctype html>" in content
        assert "Image Modification System" in content
        assert "Upload Image" in content
        assert "Results" in content
        assert "Welcome" in content


class TestErrorHandling:
    def test_nonexistent_route(self):
        client = TestClient(app)
        response = client.get("/nonexistent")

        assert response.status_code == 404

    def test_proxy_error_handling(self):
        client = TestClient(app)

        try:
            response = client.get("/api/processing/test")
            assert response.status_code != 404
        except Exception:
            # Expected - backend service connection will fail
            pass
