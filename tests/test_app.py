import pytest
from app import create_app
from app.db import get_db

@pytest.fixture()
def app(tmp_path):
    return create_app({
        "TESTING": True,
        "DATABASE": str(tmp_path/"test.db"),
        "RATE_LIMIT_MAX": 3,
        "RATE_LIMIT_WINDOW_SECONDS": 60,
    })

@pytest.fixture()
def client(app):
    return app.test_client()

def test_baseline_exposes_protected_data(client):
    r=client.get("/baseline/demo-card")
    assert r.status_code==200 and b"Synthetic Contact" in r.data

def test_public_layer_hides_protected_data(client):
    r=client.get("/tap/demo-token-001")
    assert r.status_code==200 and b"Synthetic Contact" not in r.data

def test_correct_pin_reveals_protected_data(client):
    r=client.post("/tap/demo-token-001",data={"pin":"2468"})
    assert r.status_code==200 and b"Synthetic Contact" in r.data

def test_revocation_blocks_card(app,client):
    with app.app_context():
        db=get_db();db.execute("UPDATE cards SET active=0");db.commit()
    assert client.get("/tap/demo-token-001").status_code==403

def test_rate_limit(client):
    for _ in range(3):
        assert client.post("/tap/demo-token-001",data={"pin":"0000"}).status_code==200
    assert client.post("/tap/demo-token-001",data={"pin":"0000"}).status_code==429

def test_nfc_route_redirects_and_logs(app, client):
    response = client.get("/nfc/demo-token-001", follow_redirects=False)
    assert response.status_code == 302
    assert "/tap/demo-token-001?from_nfc=1" in response.headers["Location"]
    with app.app_context():
        row = get_db().execute(
            "SELECT * FROM audit_events WHERE event_type='nfc_tap' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        assert row is not None
        assert row["outcome"] == "allowed"


def test_unknown_nfc_token_is_denied(app, client):
    response = client.get("/nfc/not-a-real-token")
    assert response.status_code == 404
    with app.app_context():
        row = get_db().execute(
            "SELECT * FROM audit_events WHERE event_type='nfc_tap' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        assert row is not None
        assert row["outcome"] == "denied"
