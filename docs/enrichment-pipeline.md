# Canonical Research and Enrichment Pipeline

## Run 6.1 production research

The source check resolves a coaster against multiple Wikidata queries and languages,
ranks matches using coaster name, park and entity description, and rejects ambiguous
results instead of accepting the first hit. A confirmed entity can discover the
coaster-specific official URL (`P856`) and RCDB record (`P2751`). Manually supplied URLs
take precedence and remain visible in the stored job report.

RCDB and explicitly labelled page facts are parsed deterministically before AI runs.
Wikidata and RCDB therefore remain useful with AI switched off. AI supplements these
facts for unstructured official prose and compares assertions; it never becomes a source
itself. Selecting AI without `COASTER_OPENAI_API_KEY` returns a clear validation error.

Every source report records requested and final URL, discovery method, HTTP status, page
title, entity match, deterministic and AI assertion counts, and a precise rejection
reason. A general park homepage is never substituted for a coaster-specific official page.

Production acceptance includes manually reviewed checks for Python (`Q15727`, RCDB `897`)
and Baron 1898 (`Q18285730`, RCDB `12083`), plus ambiguous names, missing official URLs,
an incorrect RCDB URL, and an official page without deterministic facts.

## Principle

Sources do not define truth. They provide field-level assertions. Coaster Capital
identifies the entity, compares assertions and proposes the most likely canonical
value. Wikidata, Wikipedia, official park or manufacturer material, RCDB and
specialist sources are inputs without a globally fixed source order.

This release establishes the generic governance layer for coasters, parks and
manufacturers. The existing Wikimedia adapter remains the first connected adapter;
it is not treated as a preferred or canonical source. Additional adapters and the
OpenAI synthesis service can feed the same assertion model without changing the
canonical tables or review workflow.

## Confidence

Confidence is calculated per field. It is a reproducible evidence score, not an
unsupported language-model confidence claim.

| Score | Classification | Default handling |
|---:|---|---|
| 0–19% | Reject | Automatically reject as a canonical candidate |
| 20–44% | Probably incorrect | Retain as weak evidence |
| 45–69% | Needs review | Mandatory manual review |
| 70–89% | Probably correct | Accelerated manual review |
| 90–94% | Very probably correct | Manual confirmation |
| 95–100% | Very probably correct | Auto-approval may be eligible |

The weighted components are entity match (20%), field-specific source quality
(25%), source agreement (25%), semantic fit (15%), freshness (10%) and technical
validation (5%).

Auto-approval additionally requires:

- entity match of at least 98%;
- two suitable independent sources or one explicit primary source;
- no unresolved conflict;
- successful type, unit and plausibility validation;
- automation class A at 95% or class B at 97%;
- no active protected manual override.

Class C fields are never auto-approved.

## Data catalog

`GET /v1/admin/enrichment/catalog` exposes exact field definitions, units,
validation ranges and the automation class for coasters, parks and manufacturers.
The catalog deliberately distinguishes construction height from drop and regular
public opening from previews.

## Review decisions

An editor can accept, edit and accept, reject, mark insufficient evidence or defer
a proposal. An edited value requires a reason and creates a protected canonical
override. Later research may create a dispute proposal, but cannot silently
overwrite the correction.

Proposed, reviewed and source-asserted values remain separately traceable.

## Persistence

The migration adds generic entity references, score breakdowns, confidence and
automation classes, conflict flags, external identifiers and canonical overrides.
The existing `coaster_id` remains nullable for backward compatibility with Run 4.

## Connected and Pending Layers

Connected in this release:

- Wikimedia lookup with the policy-compliant identifying headers from hotfix #6;
- field-level assertions and source URLs;
- generic scoring, validation, review and audit behavior.

Deliberately pending for the next source-integration run:

- official park/manufacturer website adapters;
- RCDB and other specialist-source adapters subject to their access terms;
- OpenAI structured synthesis across collected assertions;
- calibrated source-quality profiles per field;
- ambiguous entity candidate selection in the UI.

Until those adapters are connected, a single Wikimedia assertion remains a manual
review proposal and can never meet the evidence rule for automatic approval.
# Run 6 — operational source research

Run 6 connects the Run 5 evidence and governance model to real source adapters.
The canonical catalogue is still changed only through automatic approval that
passes every guardrail or through an explicit administrator decision.

## Supported source adapters

| Adapter | Input | Role | Primary source |
|---|---|---|---|
| Wikimedia | optional Wikidata QID, otherwise entity search | structured claims and encyclopedic context | no |
| Official | explicit HTTPS URL or saved park/manufacturer website | authoritative park or manufacturer assertion | yes |
| RCDB | explicit `https://rcdb.com/...` record URL | specialist secondary assertion | no |
| OpenAI | text fetched from the sources above | extraction and comparison only | never |

The OpenAI layer cannot browse independently. It receives source text, the entity
identity, the data-catalogue definition and the permitted output fields. Every
extracted assertion retains the original webpage URL and a short supporting quote.
The model output itself is not stored as source evidence.

## Production configuration

Add these variables to the API service:

```text
COASTER_OPENAI_API_KEY=<secret>
COASTER_OPENAI_MODEL=gpt-5.6-sol
COASTER_RESEARCH_TIMEOUT_SECONDS=25
COASTER_RESEARCH_MAX_PAGE_BYTES=1500000
```

`COASTER_OPENAI_API_KEY` is optional. Without it, Wikimedia assertions still work
and source jobs remain reviewable, but HTML pages cannot be converted into field
assertions. The admin UI reports `disabled_no_key`; the job does not pretend that
AI research occurred.

After deploying the variables, run:

```bash
cd apps/api
alembic upgrade head
```

The expected migration head is `c6a5e2f84b17`.

## Administrator workflow

1. Open **Admin → Enrichment** and select coaster, park or manufacturer.
2. Optionally enter a known Wikidata QID.
3. Enter the exact official detail page. A saved park or manufacturer homepage is
   used only when no explicit URL is supplied.
4. For a coaster, enter its exact RCDB record URL when known.
5. Leave AI comparison enabled and start the source check.
6. Check the source-state chips. A failed adapter does not invalidate assertions
   successfully collected from another adapter.
7. Review conflicts and the supporting source assertions per field.
8. Correct with a reason, accept, reject, mark insufficient, or defer.

Use detail pages rather than general homepages. Extraction quality depends on the
page actually containing explicit facts.

## Safety and failure behaviour

- Only public HTTPS URLs are fetched.
- Credentials in URLs, localhost, private IPs and reserved IPs are blocked.
- Redirect targets are validated again.
- RCDB URLs must remain on `rcdb.com`.
- Only HTML is accepted and response size is capped.
- Source and AI failures are recorded in `source_report`.
- No assertions means a failed job and no canonical mutation.
- Conflicting values always block automatic approval.
- Existing manual overrides remain protected.
- AI may select only from supplied evidence and never satisfies the independent
  source requirement by itself.

## Operational rollout

Start with 25 known coasters across at least five parks. Include easy records,
height/drop ambiguity, renamed rides, relocated rides, closed rides and records
with known source disagreement. Review every proposal manually during this pilot.
Record false positives by field and source type. Enable automatic acceptance only
after the resulting confidence calibration is reviewed.
