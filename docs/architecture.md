# Coaster Capital v2 architecture

## Product boundary

Coaster Capital is one data platform with three consumers:

1. a public discovery website;
2. an editorial and review application;
3. a versioned API for integrations and future commercial access.

All consumers use the same canonical definitions. UI code never becomes the source of
truth for coaster data.

## Runtime topology

| Component | Responsibility | Initial platform |
| --- | --- | --- |
| `apps/web` | Public website and admin interface | Vercel |
| `apps/api` | Canonical reads, writes and review rules | Render |
| `workers` | Crawling, extraction, imports and exports | Render workers |
| PostgreSQL | Canonical records, provenance and audit history | Neon |
| CDN/API edge | Caching, WAF and customer rate limits | Cloudflare |

Docker is not required for local development. Each application has a native runtime and
can be deployed directly from GitHub.

## Architectural rules

- AI never writes directly to canonical entity tables.
- Every proposed value has provenance, extraction time and review state.
- Canonical changes create append-only audit events.
- Public reads and editorial writes can scale independently.
- External APIs are versioned from their first release.
- Commercial visibility is explicit per field and source licence.
- Stable identifiers do not encode names or mutable business meaning.

## Run 1 scope

Run 1 establishes the repository, Material Design 3 foundations, public and admin shells,
FastAPI contract and deployment boundaries. It intentionally does not yet implement CRUD,
authentication, crawling or canonical database migrations.

