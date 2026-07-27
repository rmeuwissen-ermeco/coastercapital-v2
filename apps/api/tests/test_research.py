import json
import socket

import httpx
import pytest

from app import models, research
from app.config import Settings
from app.enrichment import EvidenceCandidate


def _public_dns(*_args, **_kwargs):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]


def test_source_url_security_blocks_private_and_non_https(monkeypatch) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))],
    )
    with pytest.raises(research.ResearchError):
        research.validate_public_https_url("https://example.com/source")
    with pytest.raises(research.ResearchError):
        research.validate_public_https_url("http://rcdb.com/123.htm", rcdb_only=True)


def test_rcdb_adapter_rejects_other_hosts(monkeypatch) -> None:
    monkeypatch.setattr(socket, "getaddrinfo", _public_dns)
    with pytest.raises(research.ResearchError):
        research.validate_public_https_url("https://example.com/pretend-rcdb", rcdb_only=True)
    assert (
        research.validate_public_https_url("https://rcdb.com/123.htm", rcdb_only=True)
        == "https://rcdb.com/123.htm"
    )


def test_page_fetch_strips_active_markup(monkeypatch) -> None:
    monkeypatch.setattr(socket, "getaddrinfo", _public_dns)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            text="<h1>Baron 1898</h1><script>ignore()</script><p>Drop 37.5 m</p>",
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        text = research.fetch_page_text(
            research.PageSource("official", "https://example.com/baron", "Park", True),
            Settings(),
            client=client,
        )
    assert text == "Baron 1898 Drop 37.5 m"


def test_ai_extraction_keeps_webpage_as_source(monkeypatch) -> None:
    monkeypatch.setattr(socket, "getaddrinfo", _public_dns)
    output = {
        "assertions": [
            {
                "field_name": "drop_m",
                "value": 37.5,
                "quote": "a free fall of 37.5 metres",
                "confidence": 0.98,
            }
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"output": [{"content": [{"type": "output_text", "text": json.dumps(output)}]}]},
            request=request,
        )

    settings = Settings(openai_api_key="test", openai_model="test-model")
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        candidates = research.extract_assertions(
            entity_type=models.EnrichmentEntityType.COASTER,
            entity_name="Baron 1898",
            context_name="Efteling",
            source=research.PageSource(
                "official", "https://example.com/baron", "Official park", True
            ),
            page_text="Baron 1898 has a free fall of 37.5 metres.",
            settings=settings,
            client=client,
        )
    assert candidates[0].source_type == "official"
    assert candidates[0].source_url == "https://example.com/baron"
    assert candidates[0].is_primary is True
    assert candidates[0].raw_value["quote"] == "a free fall of 37.5 metres"


def test_distinct_values_detects_conflict() -> None:
    shared = {
        "field_name": "height_m",
        "source_label": "Source",
        "confidence": 0.9,
        "raw_value": {},
    }
    candidates = [
        EvidenceCandidate(
            value=30,
            source_type="official",
            source_url="https://park.example/ride",
            **shared,
        ),
        EvidenceCandidate(
            value=37.5,
            source_type="rcdb",
            source_url="https://rcdb.com/123.htm",
            **shared,
        ),
    ]
    assert len(research.distinct_values(candidates)) == 2


def test_rcdb_deterministic_extractor_works_without_openai_key() -> None:
    text = (
        "Baron 1898 - Efteling Operating since 7/1/2015 Roller Coaster. "
        "Length 1,643.7 ft Height 98.4 ft Drop 123.0 ft Speed 55.9 mph "
        "Inversions 2 Capacity 1000 riders per hour"
    )
    candidates = research.deterministic_assertions(
        entity_type=models.EnrichmentEntityType.COASTER,
        entity_name="Baron 1898",
        context_name="Efteling",
        source=research.PageSource(
            "rcdb", "https://rcdb.com/12083.htm", "RCDB · Baron 1898", False
        ),
        page_text=text,
    )
    values = {item.field_name: item.value for item in candidates}
    assert values["opened_on"] == "2015-07-01"
    assert values["height_m"] == pytest.approx(29.992)
    assert values["drop_m"] == pytest.approx(37.49)
    assert values["speed_kmh"] == pytest.approx(89.962)
    assert values["length_m"] == pytest.approx(501.0, abs=0.1)
    assert values["inversions"] == 2
    assert values["capacity_pph"] == 1000


def test_deterministic_extractor_rejects_wrong_rcdb_record() -> None:
    with pytest.raises(research.ResearchError, match="selected coaster"):
        research.deterministic_assertions(
            entity_type=models.EnrichmentEntityType.COASTER,
            entity_name="Python",
            context_name="Efteling",
            source=research.PageSource("rcdb", "https://rcdb.com/12083.htm", "RCDB", False),
            page_text="Baron 1898 - Efteling Height 98.4 ft",
        )
