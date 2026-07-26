# Coaster Capital v2

AI-powered, source-driven roller coaster database and community platform.

## Repository

- `apps/web`: Next.js public website and administration interface.
- `apps/api`: FastAPI canonical data and review API.
- `workers`: reserved for crawler, extraction and export workers.
- `docs`: architecture and domain decisions.

The project deploys from GitHub to managed services. Docker is not required for local
development.

## Requirements

- Node.js 24 or newer
- Python 3.12 or newer

## Web application

```bash
npm install
cp apps/web/.env.example apps/web/.env.local
npm run dev
```

Open <http://localhost:3000>.

## API

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000/health> or <http://127.0.0.1:8000/docs>.

## Current status

Run 4 adds a review-first Wikidata and Wikipedia enrichment pipeline to the secured
catalogue. Every proposed field value retains source evidence and confidence metadata;
canonical data changes only after explicit approval and every decision is audited.

## Managed deployment

- Vercel deploys `apps/web`; set `NEXT_PUBLIC_API_URL` to the public Render API URL.
- Render deploys `apps/api`; use the commands and environment variables in
  [`docs/deployment.md`](docs/deployment.md).
- Neon provides PostgreSQL; no local or production Docker setup is required.
