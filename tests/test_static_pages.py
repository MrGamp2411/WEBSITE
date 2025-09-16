from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402


PAGES = [
    ("/about", "About SiplyGo"),
    ("/help-center", "Help Center"),
    ("/for-bars", "For Bars"),
    ("/terms", "Terms of Use"),
]


def test_footer_pages_render():
    with TestClient(app) as client:
        for path, heading in PAGES:
            response = client.get(path)
            assert response.status_code == 200
            assert heading in response.text
