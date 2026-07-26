# Canonical Research and Enrichment Pipeline

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
