import httpx

from app import enrichment


def _claim(value: object, value_type: str = "string") -> dict:
    return {
        "mainsnak": {
            "snaktype": "value",
            "datavalue": {"value": value, "type": value_type},
        }
    }


def test_wikidata_match_discovers_official_and_rcdb_urls() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "www.wikidata.org" and request.url.path == "/w/api.php":
            return httpx.Response(
                200,
                json={
                    "search": [
                        {
                            "id": "Q28865",
                            "label": "Python",
                            "description": "programming language",
                        },
                        {
                            "id": "Q15727",
                            "label": "Python",
                            "description": "roller coaster at Efteling",
                        },
                    ]
                },
                request=request,
            )
        if request.url.path.endswith("/Q15727.json"):
            return httpx.Response(
                200,
                json={
                    "entities": {
                        "Q15727": {
                            "id": "Q15727",
                            "labels": {"en": {"value": "Python"}},
                            "claims": {
                                "P856": [
                                    _claim("https://www.efteling.com/en/park/attractions/python")
                                ],
                                "P2751": [_claim("897", "external-id")],
                            },
                            "sitelinks": {},
                        }
                    }
                },
                request=request,
            )
        raise AssertionError(f"Unexpected request: {request.url}")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = enrichment.fetch_wikimedia_result(
            coaster_name="Python",
            park_name="Efteling",
            client=client,
        )
    assert result.qid == "Q15727"
    assert result.match_confidence >= 0.9
    assert result.official_url == "https://www.efteling.com/en/park/attractions/python"
    assert result.rcdb_url == "https://rcdb.com/897.htm"


def test_ambiguous_wikidata_result_is_not_silently_accepted() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "search": [
                    {
                        "id": "Q28865",
                        "label": "Python",
                        "description": "programming language",
                    }
                ]
            },
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        try:
            enrichment.fetch_wikimedia_result(
                coaster_name="Python",
                park_name="Efteling",
                client=client,
            )
        except enrichment.EnrichmentLookupError as exc:
            assert "No sufficiently reliable Wikidata match" in str(exc)
        else:
            raise AssertionError("Ambiguous entity was accepted")
