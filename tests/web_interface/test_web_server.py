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
        response = client.get("/")
        assert response.status_code == 200
        assert '<div id="root"></div>' in response.text

    def test_static_js_accessible(self):
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        assert 'type="module"' in response.text


class TestErrorHandling:
    def test_nonexistent_route(self):
        client = TestClient(app)
        response = client.get("/nonexistent")

        assert response.status_code == 404
