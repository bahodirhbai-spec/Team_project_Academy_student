"""Lightweight checks for the profile page assets.

The API tests cover behaviour; these checks catch a broken script or a
control that was added to the page but never wired up in JavaScript.
"""

import shutil
import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

from backend.config.settings import Settings
from backend.main import create_app

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND = PROJECT_ROOT / "frontend"


def test_app_js_has_valid_syntax():
    if shutil.which("node") is None:
        return  # Node is not a project dependency; skip on machines without it
    subprocess.run(
        ["node", "--check", str(FRONTEND / "app.js")], check=True
    )


def test_profile_controls_are_present_and_wired():
    html = (FRONTEND / "index.html").read_text()
    script = (FRONTEND / "app.js").read_text()
    for element_id in (
        "profile-section",
        "profile-back",
        "profile-content",
    ):
        assert f'id="{element_id}"' in html
        assert element_id in script
    assert "View Profile" in script
    assert "getProfile" in script


def test_index_page_serves_profile_section(tmp_path):
    settings = Settings(
        database_path=tmp_path / "static.db", frontend_directory=FRONTEND
    )
    with TestClient(create_app(settings)) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert 'id="profile-section"' in response.text
    assert "app.js?v=6" in response.text
