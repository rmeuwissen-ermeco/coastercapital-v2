from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth import hash_password
from app.models import User, UserRole


def test_login_me_and_audit_log(client: TestClient, db: Session) -> None:
    db.add(
        User(
            email="admin@example.com",
            password_hash=hash_password("correct-horse-battery-staple"),
            role=UserRole.ADMIN,
        )
    )
    db.commit()

    login = client.post(
        "/v1/auth/login",
        json={
            "email": "ADMIN@example.com",
            "password": "correct-horse-battery-staple",
        },
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me = client.get("/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["role"] == "admin"

    park = client.post(
        "/v1/parks",
        json={"name": "Walibi Holland", "slug": "walibi-holland"},
        headers=headers,
    )
    assert park.status_code == 201

    audit = client.get("/v1/admin/audit-events", headers=headers)
    assert audit.status_code == 200
    assert audit.json()[0]["action"] == "create"
    assert audit.json()[0]["entity_type"] == "park"


def test_invalid_login_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/v1/auth/login",
        json={"email": "nobody@example.com", "password": "incorrect-password"},
    )

    assert response.status_code == 401
