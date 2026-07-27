from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

import httpx

WIKIDATA_API = "https://www.wikidata.org/w/api.php"
WIKIDATA_ENTITY = "https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
WIKIPEDIA_SUMMARY = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
WIKIMEDIA_HEADERS = {
    "User-Agent": (
        "CoasterCapital/1.0 "
        "(https://github.com/rmeuwissen-ermeco/coastercapital-v2; "
        "contact@ermeco.nl)"
    ),
    "Api-User-Agent": (
        "CoasterCapital/1.0 "
        "(https://github.com/rmeuwissen-ermeco/coastercapital-v2; "
        "contact@ermeco.nl)"
    ),
    "Accept": "application/json",
}


@dataclass(frozen=True)
class EvidenceCandidate:
    field_name: str
    value: str | float | int
    source_type: str
    source_url: str
    source_label: str
    confidence: float
    raw_value: Any
    is_primary: bool = False
    independence_key: str | None = None


class EnrichmentLookupError(RuntimeError):
    pass


@dataclass(frozen=True)
class WikimediaResult:
    qid: str
    wikipedia_title: str | None
    candidates: list[EvidenceCandidate]
    official_url: str | None
    rcdb_url: str | None
    match_confidence: float
    match_reason: str


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
    elif unit.endswith("/Q828224"):  # kilometre
        amount *= 1000
    elif not (unit.endswith("/Q11573") or unit == "1"):  # metre or unitless SI
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
    result = fetch_wikimedia_result(
        coaster_name=coaster_name,
        park_name=park_name,
        wikidata_id=wikidata_id,
        client=client,
    )
    return result.qid, result.wikipedia_title, result.candidates


def fetch_wikimedia_result(
    *,
    coaster_name: str,
    park_name: str,
    wikidata_id: str | None = None,
    client: httpx.Client | None = None,
) -> WikimediaResult:
    owns_client = client is None
    http = client or httpx.Client(timeout=20, headers=WIKIMEDIA_HEADERS, follow_redirects=True)
    try:
        qid, match_confidence, match_reason = (
            (wikidata_id, 0.99, "Wikidata ID supplied by editor")
            if wikidata_id
            else _find_wikidata_id(http, coaster_name, park_name)
        )
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
        return WikimediaResult(
            qid=qid,
            wikipedia_title=wikipedia_title,
            candidates=candidates,
            official_url=_string_claim(entity, "P856"),
            rcdb_url=_rcdb_url(entity),
            match_confidence=match_confidence,
            match_reason=match_reason,
        )
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
        raise EnrichmentLookupError(f"Source lookup failed: {exc}") from exc
    finally:
        if owns_client:
            http.close()


def _find_wikidata_id(
    http: httpx.Client, coaster_name: str, park_name: str
) -> tuple[str, float, str]:
    results: dict[str, dict[str, Any]] = {}
    for query in (f"{coaster_name} {park_name}", coaster_name):
        for language in ("en", "nl"):
            response = http.get(
                WIKIDATA_API,
                headers=WIKIMEDIA_HEADERS,
                params={
                    "action": "wbsearchentities",
                    "search": query,
                    "language": language,
                    "format": "json",
                    "limit": 10,
                },
            )
            response.raise_for_status()
            for item in response.json().get("search", []):
                results[str(item["id"])] = item
    if not results:
        raise EnrichmentLookupError("No matching Wikidata entity found")
    ranked = sorted(
        ((_search_score(item, coaster_name, park_name), item) for item in results.values()),
        key=lambda pair: pair[0],
        reverse=True,
    )
    score, best = ranked[0]
    if score < 0.72:
        alternatives = ", ".join(
            f"{item.get('label', item['id'])} ({item['id']})" for _, item in ranked[:3]
        )
        raise EnrichmentLookupError(
            f"No sufficiently reliable Wikidata match. Best candidates: {alternatives or 'none'}"
        )
    return (
        str(best["id"]),
        min(0.97, score),
        (
            f"Matched label “{best.get('label', best['id'])}” and description "
            f"“{best.get('description', '')}” against {coaster_name} at {park_name}"
        ),
    )


def _normalise_name(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())


def _search_score(item: dict[str, Any], coaster_name: str, park_name: str) -> float:
    label = str(item.get("label", ""))
    aliases = [str(value) for value in item.get("aliases", [])]
    description = str(item.get("description", ""))
    target = _normalise_name(coaster_name)
    names = [_normalise_name(label), *(_normalise_name(value) for value in aliases)]
    name_score = 0.65 if target in names else 0.45 if any(target in name for name in names) else 0
    context = f"{label} {description}".casefold()
    park_score = 0.20 if park_name.casefold() in context else 0
    type_score = (
        0.15
        if any(word in context for word in ("roller coaster", "rollercoaster", "achtbaan"))
        else 0
    )
    return name_score + park_score + type_score


def _string_claim(entity: dict[str, Any], property_id: str) -> str | None:
    claim = _claim_value(entity, property_id)
    if claim is None:
        return None
    value, _ = claim
    return value if isinstance(value, str) and value.strip() else None


def _rcdb_url(entity: dict[str, Any]) -> str | None:
    rcdb_id = _string_claim(entity, "P2751")
    return f"https://rcdb.com/{rcdb_id}.htm" if rcdb_id and rcdb_id.isdigit() else None


def _wikidata_candidates(entity: dict[str, Any], source_url: str) -> list[EvidenceCandidate]:
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


def _wikipedia_summary(http: httpx.Client, title: str) -> EvidenceCandidate | None:
    response = http.get(
        WIKIPEDIA_SUMMARY.format(title=quote(title, safe="")),
        headers=WIKIMEDIA_HEADERS,
    )
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
