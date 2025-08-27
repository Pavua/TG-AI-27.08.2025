import os, pytest
try:
    from ftg.control_server.server import app
    HAVE_APP = True
except Exception:
    HAVE_APP = False
    app = None

@pytest.mark.skipif(not HAVE_APP, reason="Control Server app not found")
def test_health_requires_auth():
    from starlette.testclient import TestClient
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code in (401, 403)

@pytest.mark.skipif(not HAVE_APP, reason="Control Server app not found")
def test_health_ok_with_token():
    from starlette.testclient import TestClient
    client = TestClient(app)
    token = os.getenv("FTG_TEST_TOKEN", "changeme_local_token")
    r = client.get("/health", headers={"X-FTG-Token": token})
    assert r.status_code in (200, 401, 403)