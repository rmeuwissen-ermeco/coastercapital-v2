from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

import httpx

WIKIDATA_API = "https://www.wikidata.org/w/api.php"
WIKIDATA_ENTITY = "https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
WIKIPEDIA_SUMMARY = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
WIKIMEDIA_HEADERS = {\n    "User-Agent": (\n        "CoasterCapital/1.0 " \n        "(https://github.com/rmeuwissen-ermeco/coastercapital-v2; " \n        "source-driven enrichment)"\n    ),\n    "Accept": "application/json",\n}


@dataclass(frozen=True)
class EvidenceCandidate:
    field_name: str
    value: str | float | int
    source_type: str
    source_url: str
    source_label: str
    confidence: float
    raw_value: Any


class EnrichmentLookupError(RuntimeError):
    pass


def _claim_value(entity: dict[str, Any], property_id: str) -> tuple[Any, str | None] | None:
    claims = entity.get("claims", {}).get(property_id, [])
    for claim in claims:
        mainsnak = claim.get("mainsnak", {})
        if mainsnak.get("snaktype") != "value":
            continue
        datavalue = mainsnak.get("datavalue", {})
        return datavalue.get("value"), datavalue.get("type")
    return None


def _quantity(value: Any) -> tuple[float, str] | None:
    if not isinstance(value, dict) or "amount" not in value:
        return None
    return float(value["amount"]), str(value.get("unit", "1"))


def _normalise_quantity(value: Any, field_name: str) -> float | None:
    parsed = _quantity(value)
    if parsed is None:
        return None
    amount, unit = parsed
    if field_name == "speed_kmh":
        if unit.endswith("/Q182429"):  # metre per second
            amount *= 3.6
        elif not unit.endswith("/Q180154"):  # kilometre per hour
            return None
    elif not (unit.endswith(("/Q11573", "/Q828224")) or unit == "1"):
        # Metre or kilometre. Wikidata normally stores SI-converted amounts, but
        # unknown units are rejected instead of guessed.
        if unit.endswith("/Q828224"):
            amount *= 1000
        else:
            return None
    return round(amount, 3)


def _time(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    raw = str(value.get("time", "")).lstrip("+")
    return raw[:10] if len(raw) >= 10 else None


def _label(entity: dict[str, Any]) -> str:
    labels = entity.get("labels", {})
    return (
        labels.get("nl", {}).get("value")
        or labels.get("en", {}).get("value")
        or entity.get("id", "Wikidata")
    )


def fetch_candidates(
    *,
    coaster_name: str,
    park_name: str,
    wikidata_id: str | None = None,
    client: httpx.Client | None = None,
) -> tuple[str, str | None, list[EvidenceCandidate]]:
    owns_client = client is None
    http = client or httpx.Client(timeout=20, headers=WIKIMEDIA_HEADERS)
    try:
        qid = wikidata_id or _find_wikidata_id(http, coaster_name, park_name)
        entity_url = WIKIDATA_ENTITY.format(qid=qid)
        response = http.get(entity_url, headers=WIKIMEDIA_HEADERS)
        response.raise_for_status()
        entity = response.json()["entities"][qid]
        candidates = _wikidata_candidates(entity, entity_url)
        wikipedia_title = _wikipedia_title(entity)
        if wikipedia_title:
            candidate = _wikipedia_summary(http, wikipedia_title)
            if candidate:
                candidates.append(candidate)
        return qid, wikipedia_title, candidates
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
        raise EnrichmentLookupError(f"Source lookup failed: {exc}") from exc
    finally:
        if owns_client:
            http.close()


def _find_wikidata_id(http: httpx.Client, coaster_name: str, park_name: str) -> str:
    response = http.get(
        WIKIDATA_API,
        params={
            "action": "wbsearchentities",
            "search": f"{coaster_name} {park_name}",
            "language": "en",
            "format": "json",
            "limit": 5,
        },
    )
    response.raise_for_status()
    results = response.json().get("search", [])
    if not results:
        raise EnrichmentLookupError("No matching Wikidata entity found")
    return str(results[0]["id"])


def _wikidata_candidates(
    entity: dict[str, Any], source_url: str
) -> list[EvidenceCandidate]:
    mappings = {
        "opened_on": ("P571", _time),
        "height_m": ("P2048", lambda value: _normalise_quantity(value, "height_m")),
        "length_m": ("P2043", lambda value: _normalise_quantity(value, "length_m")),
        "speed_kmh": ("P2052", lambda value: _normalise_quantity(value, "speed_kmh")),
    }
    candidates: list[EvidenceCandidate] = []
    for field_name, (property_id, normaliser) in mappings.items():
        claim = _claim_value(entity, property_id)
        if claim is None:
            continue
        raw_value, _ = claim
        value = normaliser(raw_value)
        if value is None:
            continue
        candidates.append(
            EvidenceCandidate(
                field_name=field_name,
                value=value,
                source_type="wikidata",
                source_url=source_url,
                source_label=f"{_label(entity)} · {property_id}",
                confidence=0.82,
                raw_value=raw_value,
            )
        )
    return candidates


def _wikipedia_title(entity: dict[str, Any]) -> str | None:
    sitelinks = entity.get("sitelinks", {})
    page = sitelinks.get("nlwiki") or sitelinks.get("enwiki")
    return str(page["title"]) if page and page.get("title") else None


def _wikipedia_summary(
    http: httpx.Client, title: str
) -> EvidenceCandidate | None:
    response = http.get(\n        WIKIPEDIA_SUMMARY.format(title=quote(title, safe="")),\n        headers=WIKIMEDIA_HEADERS,\n    )
    if response.status_code == 404:
        return None
    response.raise_for_status()
    data = response.json()
    summary = str(data.get("extract", "")).strip()
    page_url = data.get("content_urls", {}).get("desktop", {}).get("page")
    if not summary or not page_url:
        return None
    return EvidenceCandidate(
        field_name="summary",
        value=summary,
        source_type="wikipedia",
        source_url=str(page_url),
        source_label=title,
        confidence=0.72,
        raw_value={"title": title, "retrieved_at": datetime.now(UTC).isoformat()},
    )
