from fastapi.testclient import TestClient


def test_catalogue_flow(client: TestClient) -> None:
    park_response = client.post(
        "/v1/parks",
        json={
            "name": "Efteling",
            "slug": "efteling",
            "city": "Kaatsheuvel",
            "website_url": "https://www.efteling.com/",
            "summary": "Theme park in the Netherlands.",
        },
    )
    assert park_response.status_code == 201
    park = park_response.json()

    manufacturer_response = client.post(
        "/v1/manufacturers",
        json={
            "name": "Bolliger & Mabillard",
            "slug": "bolliger-mabillard",
            "founded_year": 1988,
            "website_url": "https://www.bolliger-mabillard.com/",
        },
    )
    assert manufacturer_response.status_code == 201
    manufacturer = manufacturer_response.json()

    coaster_response = client.post(
        "/v1/coasters",
        json={
            "name": "Baron 1898",
            "slug": "baron-1898",
            "park_id": park["id"],
            "manufacturer_id": manufacturer["id"],
            "status": "operating",
            "opened_on": "2015-07-01",
            "height_m": 37.5,
            "speed_kmh": 90,
            "inversions": 2,
        },
    )
    assert coaster_response.status_code == 201
    coaster = coaster_response.json()
    assert coaster["park"]["name"] == "Efteling"
    assert coaster["manufacturer"]["name"] == "Bolliger & Mabillard"

    search_response = client.get("/v1/search", params={"query": "Baron"})
    assert search_response.status_code == 200
    assert search_response.json()[0]["name"] == "Baron 1898"

    stats_response = client.get("/v1/stats")
    assert stats_response.json() == {"parks": 1, "manufacturers": 1, "coasters": 1}


def test_duplicate_park_slug_returns_conflict(client: TestClient) -> None:
    payload = {"name": "Efteling", "slug": "efteling"}
    assert client.post("/v1/parks", json=payload).status_code == 201
    response = client.post("/v1/parks", json=payload)
    assert response.status_code == 409


def test_invalid_coordinates_are_rejected(client: TestClient) -> None:
    response = client.post(
        "/v1/parks",
        json={"name": "Invalid park", "slug": "invalid-park", "latitude": 100},
    )
    assert response.status_code == 422
