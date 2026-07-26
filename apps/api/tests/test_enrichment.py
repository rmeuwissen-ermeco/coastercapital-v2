from fastapi.testclient import TestClient

from app.enrichment import EvidenceCandidate


def _coaster(client: TestClient, headers: dict[str, str]) -> dict:
    park = client.post(
        "/v1/parks",
        json={"name": "Efteling", "slug": "efteling"},
        headers=headers,
    ).json()
    manufacturer = client.post(
        "/v1/manufacturers",
        json={"name": "Bolliger & Mabillard", "slug": "bolliger-mabillard"},
        headers=headers,
    ).json()
    response = client.post(
        "/v1/coasters",
        json={
            "name": "Baron 1898",
            "slug": "baron-1898",
            "park_id": park["id"],
            "manufacturer_id": manufacturer["id"],
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def test_enrichment_requires_authentication(client: TestClient) -> None:
    assert client.get("/v1/admin/enrichment/jobs").status_code == 401


def test_source_proposal_requires_review_before_canonical_update(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
) -> None:
    coaster = _coaster(client, auth_headers)

    def fake_candidates(**_):
        return (
            "Q123",
            "Baron 1898",
            [
                EvidenceCandidate(
                    field_name="height_m",
                    value=37.5,
                    source_type="wikidata",
                    source_url="https://www.wikidata.org/wiki/Q123",
                    source_label="Baron 1898 · P2048",
                    confidence=0.82,
                    raw_value={"amount": "+37.5"},
                )
            ],
        )

    monkeypatch.setattr("app.enrichment.fetch_candidates", fake_candidates)
    run = client.post(
        "/v1/admin/enrichment/jobs",
        json={"coaster_id": coaster["id"], "wikidata_id": "Q123"},
        headers=auth_headers,
    )
    assert run.status_code == 201
    job = run.json()
    assert job["status"] == "review"
    assert job["proposals"][0]["proposal_status"] == "pending"
    assert job["proposals"][0]["evidence"][0]["source_type"] == "wikidata"

    unchanged = client.get("/v1/coasters?query=Baron").json()["items"][0]
    assert unchanged["height_m"] is None

    proposal_id = job["proposals"][0]["id"]
    accepted = client.patch(
        f"/v1/admin/enrichment/proposals/{proposal_id}",
        json={"decision": "accepted"},
        headers=auth_headers,
    )
    assert accepted.status_code == 200
    assert accepted.json()["proposal_status"] == "accepted"

    updated = client.get("/v1/coasters?query=Baron").json()["items"][0]
    assert updated["height_m"] == 37.5

    second_review = client.patch(
        f"/v1/admin/enrichment/proposals/{proposal_id}",
        json={"decision": "rejected"},
        headers=auth_headers,
    )
    assert second_review.status_code == 409

    audit = client.get("/v1/admin/audit-events", headers=auth_headers).json()
    assert audit[0]["action"] == "enrichment.accepted"


def test_rejected_proposal_does_not_change_coaster(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
) -> None:
    coaster = _coaster(client, auth_headers)
    monkeypatch.setattr(
        "app.enrichment.fetch_candidates",
        lambda **_: (
            "Q123",
            None,
            [
                EvidenceCandidate(
                    field_name="speed_kmh",
                    value=90.0,
                    source_type="wikidata",
                    source_url="https://www.wikidata.org/wiki/Q123",
                    source_label="Baron 1898 · P2052",
                    confidence=0.82,
                    raw_value={"amount": "+90"},
                )
            ],
        ),
    )
    job = client.post(
        "/v1/admin/enrichment/jobs",
        json={"coaster_id": coaster["id"]},
        headers=auth_headers,
    ).json()
    proposal_id = job["proposals"][0]["id"]
    response = client.patch(
        f"/v1/admin/enrichment/proposals/{proposal_id}",
        json={"decision": "rejected"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    current = client.get("/v1/coasters?query=Baron").json()["items"][0]
    assert current["speed_kmh"] is None
