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

## Run 3 security

Add all three authentication values to Render before deploying Run 3. Generate the JWT
secret and password independently and store them only as secret environment variables.
The idempotent seed command creates the first administrator and also supports password
rotation on a later deploy.

Add `API_URL` to Vercel Production. Admin requests then travel through the Next.js server
proxy; the short-lived JWT remains in an HttpOnly, Secure, SameSite cookie and is never
available to browser JavaScript.
