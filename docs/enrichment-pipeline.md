# AI Data Enrichment Pipeline

Run 4 introduces a review-first enrichment workflow for coaster records.

## Data flow

1. An administrator selects a canonical coaster.
2. The API resolves a Wikidata entity or uses an explicitly supplied Q-ID.
3. Structured Wikidata claims are normalised into canonical units.
4. The linked Dutch or English Wikipedia introduction is collected when available.
5. Every candidate becomes a field proposal with its current value, proposed value,
   confidence, evidence status, source URL, source type and retrieval timestamp.
6. The canonical record remains unchanged until an administrator accepts that proposal.
7. Acceptance or rejection is written to the audit log.

## Safety rules

- Source retrieval never directly overwrites catalogue data.
- Ambiguous automatic matching can be bypassed with an explicit Wikidata Q-ID.
- Unknown units are rejected instead of guessed.
- A reviewed proposal cannot be reviewed a second time.
- Re-running enrichment creates a new, historically traceable job.
- Wikipedia prose is classified as probable and requires editorial review.

## Current source coverage

The first implementation supports Wikidata opening date, height, length and speed, plus
the linked Wikipedia introduction. The schema already supports confirmed, probable,
AI interpretation, conflicting and unknown evidence states. Additional official and
specialist adapters can be added without changing the review contract.

OpenAI generation is intentionally not enabled by default in Run 4. It will consume
reviewed facts in a later step, so generated prose and classifications remain visibly
separate from source-confirmed facts.
