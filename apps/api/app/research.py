from __future__ import annotations

import ipaddress
import json
import re
import socket
from dataclasses import dataclass
from html import unescape
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from app import data_catalog, models
from app.config import Settings
from app.enrichment import WIKIMEDIA_HEADERS, EvidenceCandidate

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
RCDB_HOSTS = {"rcdb.com", "www.rcdb.com"}
TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(r"<(script|style|svg)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
SPACE_RE = re.compile(r"\s+")
JSON_SCALAR_SCHEMA = {
    "anyOf": [
        {"type": "string"},
        {"type": "number"},
        {"type": "integer"},
    ]
}


class ResearchError(RuntimeError):
    pass


@dataclass(frozen=True)
class PageSource:
    source_type: str
    url: str
    label: str
    is_primary: bool


@dataclass(frozen=True)
class SynthesisResult:
    field_name: str
    value: Any
    confidence: float
    semantic_fit: float
    rationale: str
    supporting_indexes: tuple[int, ...]


def validate_public_https_url(url: str, *, rcdb_only: bool = False) -> str:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme != "https" or not host or parsed.username or parsed.password:
        raise ResearchError("Only public HTTPS source URLs are allowed")
    if rcdb_only and host not in RCDB_HOSTS:
        raise ResearchError("RCDB URL must use https://rcdb.com")
    if host in {"localhost", "localhost.localdomain"}:
        raise ResearchError("Local source URLs are not allowed")
    try:
        addresses = socket.getaddrinfo(host, parsed.port or 443, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ResearchError(f"Source host could not be resolved: {host}") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not ip.is_global:
            raise ResearchError("Private, loopback and reserved source addresses are blocked")
    return url


def fetch_page_text(
    source: PageSource,
    settings: Settings,
    *,
    client: httpx.Client | None = None,
) -> str:
    url = validate_public_https_url(
        source.url, rcdb_only=source.source_type == "rcdb"
    )
    owns_client = client is None
    http = client or httpx.Client(
        timeout=settings.research_timeout_seconds,
        headers=WIKIMEDIA_HEADERS,
        follow_redirects=False,
    )
    try:
        response = None
        current_url = url
        for _ in range(6):
            validate_public_https_url(
                current_url, rcdb_only=source.source_type == "rcdb"
            )
            response = http.get(current_url, follow_redirects=False)
            if not response.is_redirect:
                break
            location = response.headers.get("location")
            if not location:
                raise ResearchError(f"Invalid redirect from {source.label}")
            current_url = urljoin(current_url, location)
        else:
            raise ResearchError(f"Too many redirects from {source.label}")
        assert response is not None
        response.raise_for_status()
        content_type = response.headers.get("content-type", "").lower()
        if "text/html" not in content_type:
            raise ResearchError(f"Unsupported content type for {source.label}")
        if len(response.content) > settings.research_max_page_bytes:
            raise ResearchError(f"Source page is too large: {source.label}")
        return _html_to_text(response.text)
    except httpx.HTTPError as exc:
        raise ResearchError(f"Could not fetch {source.label}: {exc}") from exc
    finally:
        if owns_client:
            http.close()


def _html_to_text(html: str) -> str:
    clean = SCRIPT_RE.sub(" ", html)
    clean = TAG_RE.sub(" ", clean)
    return SPACE_RE.sub(" ", unescape(clean)).strip()[:80_000]


def extract_assertions(
    *,
    entity_type: models.EnrichmentEntityType,
    entity_name: str,
    context_name: str,
    source: PageSource,
    page_text: str,
    settings: Settings,
    client: httpx.Client | None = None,
) -> list[EvidenceCandidate]:
    if not settings.openai_api_key:
        return []
    definitions = [
        item
        for item in data_catalog.FIELDS
        if item.entity_type == entity_type
    ]
    allowed = {
        item.field_name: {
            "type": item.data_type,
            "unit": item.unit,
            "definition": item.description,
        }
        for item in definitions
    }
    schema = {
        "type": "object",
        "properties": {
            "assertions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "field_name": {"type": "string", "enum": list(allowed)},
                        "value": JSON_SCALAR_SCHEMA,
                        "quote": {"type": "string"},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                    "required": ["field_name", "value", "quote", "confidence"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["assertions"],
        "additionalProperties": False,
    }
    instructions = (
        "Extract only explicit factual assertions from the supplied webpage text. "
        "Never use prior knowledge, infer missing numbers, convert height into drop, or "
        "treat marketing language as a technical fact. Return no assertion when the "
        "entity identity is ambiguous. Preserve dates as YYYY-MM-DD when the day is stated. "
        "Use metric units; only convert a value when the source unit is explicit. The quote "
        "must be a short exact supporting fragment from the supplied text."
    )
    payload = {
        "model": settings.openai_model,
        "instructions": instructions,
        "input": json.dumps(
            {
                "entity_type": entity_type.value,
                "entity_name": entity_name,
                "context": context_name,
                "source": source.url,
                "allowed_fields": allowed,
                "page_text": page_text,
            },
            ensure_ascii=False,
        ),
        "text": {
            "format": {
                "type": "json_schema",
                "name": "source_assertions",
                "strict": True,
                "schema": schema,
            }
        },
    }
    data = _openai_response(payload, settings, client)
    result: list[EvidenceCandidate] = []
    for assertion in data.get("assertions", []):
        field_name = assertion.get("field_name")
        definition = data_catalog.field_definition(entity_type, field_name)
        value = assertion.get("value")
        if definition is None or not data_catalog.validate_value(definition, value):
            continue
        result.append(
            EvidenceCandidate(
                field_name=field_name,
                value=value,
                source_type=source.source_type,
                source_url=source.url,
                source_label=source.label,
                confidence=min(1.0, max(0.0, float(assertion["confidence"]))),
                raw_value={"quote": assertion["quote"]},
                is_primary=source.is_primary,
                independence_key=urlparse(source.url).hostname,
            )
        )
    return result


def synthesize_field(
    *,
    entity_type: models.EnrichmentEntityType,
    entity_name: str,
    field_name: str,
    candidates: list[EvidenceCandidate],
    settings: Settings,
    client: httpx.Client | None = None,
) -> SynthesisResult | None:
    if not settings.openai_api_key or not candidates:
        return None
    definition = data_catalog.field_definition(entity_type, field_name)
    if definition is None:
        return None
    evidence = [
        {
            "index": index,
            "value": item.value,
            "source_type": item.source_type,
            "source_url": item.source_url,
            "is_primary": item.is_primary,
            "source_confidence": item.confidence,
            "support": item.raw_value,
        }
        for index, item in enumerate(candidates)
    ]
    schema = {
        "type": "object",
        "properties": {
            "value": JSON_SCALAR_SCHEMA,
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "semantic_fit": {"type": "number", "minimum": 0, "maximum": 1},
            "rationale": {"type": "string"},
            "supporting_indexes": {
                "type": "array",
                "items": {"type": "integer", "minimum": 0},
            },
        },
        "required": [
            "value",
            "confidence",
            "semantic_fit",
            "rationale",
            "supporting_indexes",
        ],
        "additionalProperties": False,
    }
    payload = {
        "model": settings.openai_model,
        "instructions": (
            "Select the most defensible canonical value using only the supplied source "
            "assertions. Prefer an explicit primary source, but identify conflicts rather "
            "than averaging incompatible values. Do not add facts. Keep the rationale "
            "brief and describe why the selected assertions fit the field definition."
        ),
        "input": json.dumps(
            {
                "entity": entity_name,
                "field": field_name,
                "definition": definition.description,
                "unit": definition.unit,
                "evidence": evidence,
            },
            ensure_ascii=False,
        ),
        "text": {
            "format": {
                "type": "json_schema",
                "name": "canonical_synthesis",
                "strict": True,
                "schema": schema,
            }
        },
    }
    result = _openai_response(payload, settings, client)
    value = result.get("value")
    if not data_catalog.validate_value(definition, value):
        return None
    indexes = tuple(
        index
        for index in result.get("supporting_indexes", [])
        if isinstance(index, int) and 0 <= index < len(candidates)
    )
    if not indexes:
        return None
    return SynthesisResult(
        field_name=field_name,
        value=value,
        confidence=float(result["confidence"]),
        semantic_fit=float(result["semantic_fit"]),
        rationale=str(result["rationale"]),
        supporting_indexes=indexes,
    )


def _openai_response(
    payload: dict[str, Any],
    settings: Settings,
    client: httpx.Client | None,
) -> dict[str, Any]:
    owns_client = client is None
    http = client or httpx.Client(timeout=60)
    try:
        response = http.post(
            OPENAI_RESPONSES_URL,
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        body = response.json()
        text = body.get("output_text")
        if not text:
            for item in body.get("output", []):
                for content in item.get("content", []):
                    if content.get("type") == "output_text":
                        text = content.get("text")
                        break
        if not text:
            raise ResearchError("OpenAI returned no structured output")
        return json.loads(text)
    except (httpx.HTTPError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ResearchError(f"AI research failed: {exc}") from exc
    finally:
        if owns_client:
            http.close()


def distinct_values(candidates: list[EvidenceCandidate]) -> set[str]:
    return {
        json.dumps(item.value, sort_keys=True, ensure_ascii=False, default=str)
        for item in candidates
    }
