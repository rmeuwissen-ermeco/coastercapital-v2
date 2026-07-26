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
npm run dev
```

Open <http://localhost:3000>.

## API

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000/health> or <http://127.0.0.1:8000/docs>.

## Current status

Run 1 establishes the Material Design 3 application shell, API health contract and
architecture boundaries. CRUD, authentication and AI extraction follow in later
checkpoints.
