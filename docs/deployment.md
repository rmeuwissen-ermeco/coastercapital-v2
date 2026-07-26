# Managed deployment

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
| Build command | `pip install -e . && alembic upgrade head && python -m app.seed` |
| Start command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health check path | `/health` |

Configure these environment variables:

```text
COASTER_ENVIRONMENT=production
COASTER_AUTO_CREATE_SCHEMA=false
COASTER_DATABASE_URL=<Neon pooled PostgreSQL URL>
COASTER_CORS_ORIGINS=["https://coastercapital-v2.vercel.app"]
COASTER_JWT_SECRET=<at least 32 random characters>
COASTER_ADMIN_EMAIL=<administrator email>
COASTER_ADMIN_PASSWORD=<long random administrator password>
COASTER_OPENAI_API_KEY=<OpenAI project API key>
COASTER_OPENAI_MODEL=gpt-5.6
COASTER_RESEARCH_TIMEOUT_SECONDS=25
COASTER_RESEARCH_MAX_PAGE_BYTES=1500000
```

Migration and idempotent seeding run during every build, which also works on Render's
free service without a separate pre-deploy command.

## 3. Vercel

The project already uses `apps/web` as its root directory. Add:

```text
NEXT_PUBLIC_API_URL=https://<render-service>.onrender.com
API_URL=https://<render-service>.onrender.com
```

Apply both variables to Production, then redeploy. Public browser reads go directly to
the versioned API; authenticated admin traffic uses the server proxy.

## Verification

1. Open `https://<render-service>.onrender.com/health`.
2. Open `https://<render-service>.onrender.com/docs`.
3. Search for `Baron` on the Vercel homepage.
4. Open `/admin/data`, create a record and refresh the page.
5. Open `/admin/enrichment`, run a known coaster with its official and RCDB URLs,
   and confirm all requested source-state chips show `ok`.

## Run 6 research

Store `COASTER_OPENAI_API_KEY` only as a Render secret. OpenAI is used to extract
structured assertions from fetched official and RCDB pages and to compare those
assertions. It is not treated as an independent source.

After deployment, verify that the Render build applied migration
`c6a5e2f84b17`. First run the 25-record manual-review pilot described in
`docs/enrichment-pipeline.md`. Do not enable broad unattended enrichment until the
pilot's confidence calibration and field-level errors have been reviewed.

## Run 3 security

Add all three authentication values to Render before deploying Run 3. Generate the JWT
secret and password independently and store them only as secret environment variables.
The idempotent seed command creates the first administrator and also supports password
rotation on a later deploy.

Add `API_URL` to Vercel Production. Admin requests then travel through the Next.js server
proxy; the short-lived JWT remains in an HttpOnly, Secure, SameSite cookie and is never
available to browser JavaScript.
