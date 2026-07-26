# Run 2 managed deployment

## 1. Neon

Create a PostgreSQL project in the nearest practical EU region. Copy its pooled
connection string into Render as `COASTER_DATABASE_URL`. Keep the credential out of
GitHub, Vercel and chat.

## 2. Render web service

Connect the GitHub repository and use:

| Setting | Value |
| --- | --- |
| Root directory | `apps/api` |
| Runtime | Python |
| Build command | `pip install -e .` |
| Pre-deploy command | `alembic upgrade head` |
| Start command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health check path | `/health` |

Configure these environment variables:

```text
COASTER_ENVIRONMENT=production
COASTER_AUTO_CREATE_SCHEMA=false
COASTER_DATABASE_URL=<Neon pooled PostgreSQL URL>
COASTER_CORS_ORIGINS=["https://coastercapital-v2.vercel.app"]
```

After the first migration, run `python -m app.seed` once from a Render shell to add
the demo records. The command is safe to repeat.

## 3. Vercel

The project already uses `apps/web` as its root directory. Add:

```text
NEXT_PUBLIC_API_URL=https://<render-service>.onrender.com
```

Apply the variable to Production, Preview and Development, then redeploy. Browser
requests go directly to the versioned API; Render CORS controls which sites may call it.

## Verification

1. Open `https://<render-service>.onrender.com/health`.
2. Open `https://<render-service>.onrender.com/docs`.
3. Search for `Baron` on the Vercel homepage.
4. Open `/admin/data`, create a record and refresh the page.
