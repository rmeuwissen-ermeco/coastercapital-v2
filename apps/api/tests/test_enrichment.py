from fastapi.testclient import TestClient

from app import enrichment
from app.enrichment import EvidenceCandidate


def _wikimedia_result(
    qid: str,
    title: str | None,
    candidates: list[EvidenceCandidate],
) -> enrichment.WikimediaResult:
    return enrichment.WikimediaResult(
        qid=qid,
        wikipedia_title=title,
        candidates=candidates,
        official_url=None,
        rcdb_url=None,
        match_confidence=0.99,
        match_reason="Test fixture",
    )


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
        return _wikimedia_result(
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

    monkeypatch.setattr("app.enrichment.fetch_wikimedia_result", fake_candidates)
    run = client.post(
        "/v1/admin/enrichment/jobs",
        json={"coaster_id": coaster["id"], "wikidata_id": "Q123", "use_ai": False},
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
        "app.enrichment.fetch_wikimedia_result",
        lambda **_: _wikimedia_result(
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
        json={"coaster_id": coaster["id"], "use_ai": False},
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


def test_editor_can_correct_value_with_protected_override(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
) -> None:
    coaster = _coaster(client, auth_headers)
    monkeypatch.setattr(
        "app.enrichment.fetch_wikimedia_result",
        lambda **_: _wikimedia_result(
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
        ),
    )
    job = client.post(
        "/v1/admin/enrichment/jobs",
        json={"entity_type": "coaster", "entity_id": coaster["id"], "use_ai": False},
        headers=auth_headers,
    ).json()
    proposal_id = job["proposals"][0]["id"]

    missing_reason = client.patch(
        f"/v1/admin/enrichment/proposals/{proposal_id}",
        json={"decision": "accepted", "value": 30},
        headers=auth_headers,
    )
    assert missing_reason.status_code == 422

    corrected = client.patch(
        f"/v1/admin/enrichment/proposals/{proposal_id}",
        json={
            "decision": "accepted",
            "value": 30,
            "override_reason": "37.5 m is the drop; construction height is 30 m.",
        },
        headers=auth_headers,
    )
    assert corrected.status_code == 200
    assert corrected.json()["reviewed_value"] == 30
    assert corrected.json()["is_manual_override"] is True
    current = client.get("/v1/coasters?query=Baron").json()["items"][0]
    assert current["height_m"] == 30


def test_catalog_covers_all_three_entity_types(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.get("/v1/admin/enrichment/catalog", headers=auth_headers)
    assert response.status_code == 200
    entity_types = {item["entity_type"] for item in response.json()}
    assert entity_types == {"coaster", "park", "manufacturer"}


def test_conflicting_sources_create_one_blocked_proposal(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
) -> None:
    coaster = _coaster(client, auth_headers)
    monkeypatch.setattr(
        "app.enrichment.fetch_wikimedia_result",
        lambda **_: _wikimedia_result(
            "Q123",
            "Baron 1898",
            [
                EvidenceCandidate(
                    field_name="height_m",
                    value=30,
                    source_type="official",
                    source_url="https://www.efteling.com/baron",
                    source_label="Efteling",
                    confidence=0.99,
                    raw_value={"quote": "30 metres high"},
                    is_primary=True,
                    independence_key="efteling.com",
                ),
                EvidenceCandidate(
                    field_name="height_m",
                    value=37.5,
                    source_type="rcdb",
                    source_url="https://rcdb.com/12083.htm",
                    source_label="RCDB",
                    confidence=0.92,
                    raw_value={"quote": "Height 37.5 m"},
                    independence_key="rcdb.com",
                ),
            ],
        ),
    )
    response = client.post(
        "/v1/admin/enrichment/jobs",
        json={
            "entity_type": "coaster",
            "entity_id": coaster["id"],
            "wikidata_id": "Q123",
            "use_ai": False,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    proposal = response.json()["proposals"][0]
    assert proposal["proposed_value"] == 30
    assert proposal["has_conflict"] is True
    assert proposal["auto_approval_eligible"] is False
    assert proposal["evidence_status"] == "conflicting"
    assert len(proposal["evidence"]) == 2
