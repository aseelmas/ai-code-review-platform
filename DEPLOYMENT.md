# Deployment guide

## Recommended architecture

Use a **Render Docker Web Service** for FastAPI and a **Render Static Site** for
the React/Vite build. Both deploy independently from this repository. The backend
container includes Python 3.12, Git, and CA certificates and runs as a non-root
user. The frontend needs no Node server after building. No database or persistent
disk is needed: cloned repositories are temporary and results are returned to
the browser.

Choose a paid backend instance for production. Render's free web services sleep
after inactivity and are intended for demos/testing, not production. Start with
enough memory for concurrent clones and Python ASTs (1 GiB is a reasonable initial
budget, not a guarantee), then measure and tune. References:
[Docker deployment](https://render.com/docs/docker),
[static sites](https://render.com/docs/static-sites), and
[free-instance limitations](https://render.com/docs/free).

This change prepares packaging and configuration. It does not add authentication
or per-user rate limits. CORS is a browser policy, not access control: direct
HTTP clients can still call the API. Restrict access at your gateway before
exposing a paid AI key or expensive analysis endpoints to unrestricted traffic.

## Environment variables

### Backend (runtime)

| Variable | Local default | Production setting |
| --- | --- | --- |
| `APP_ENV` | `development` | `production` (already set in the image) |
| `CORS_ORIGINS` | Both local Vite origins on port 5173, if omitted | Comma-separated exact frontend HTTPS origins, no paths or wildcards |
| `PORT` | `8000` | Let Render supply its port |
| `LIMIT_CONCURRENCY` | `8` | Maximum Uvicorn connections/tasks per process; tune to memory capacity |
| `OPENAI_API_KEY` | Unset | Optional runtime secret; needed only for AI review |
| `OPENAI_MODEL` | `gpt-5.4` | Optional model override supported by your OpenAI account |

The production start command is **`python -m backend`**, from the repository
root. It binds `0.0.0.0`, reads `PORT`, runs one worker without reload, limits
concurrent connections/tasks, and allows 30 seconds for graceful shutdown. Under
load, Uvicorn can return 503 instead of admitting more requests. The limit also
includes health checks and idle connections; it is not a request-per-minute limit.
Do not increase worker count without considering aggregate memory/disk usage.

In development, the root `.env` is loaded without overriding already-set
environment variables. In production, `.env` is never loaded. A missing
`CORS_ORIGINS` in production means no cross-origin browser access, while health
checks still work. Invalid origins fail startup. Cookies/credentialed CORS are
disabled because this application currently has no cookie authentication.

### Frontend (build time)

Set **`VITE_API_URL`** to the public HTTPS backend base URL. A backend under a path
prefix is supported; trailing slashes are normalized. Production builds reject
missing values, localhost, HTTP, credentials, queries, and fragments. Local
`npm run dev` still defaults to `http://127.0.0.1:8000` if unset.

Vite embeds this public URL during the build. Changing it requires rebuilding
and redeploying the frontend. Never set an API key in a `VITE_` variable. See
[Vite environment variables](https://vite.dev/guide/env-and-mode).

## Validate locally before deployment

Use a working Python 3.12 installation, Git, and Node 22 (at least 22.14).
Recreate a moved/broken virtual environment instead of copying its files.
The frontend `.node-version` selects the Node 22 line, and `engines` bounds it
to that major version. Hosts can select an up-to-date patch release.

PowerShell, from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q

cd frontend
npm ci --include=dev
npm test
npm run lint
# Replace this with the real backend URL for a deployable build.
$env:VITE_API_URL = 'https://YOUR-BACKEND-HOST'
npm run build
```

For normal development, unset a production build override before starting Vite:

```powershell
Remove-Item Env:VITE_API_URL -ErrorAction SilentlyContinue
npm run dev
```

The frontend output is `frontend/dist`. `npm run preview` can inspect a build
locally; neither Vite's dev server nor preview server should serve production.
Backend development still supports `python -m uvicorn backend.main:app --reload`.

Optional Docker validation, from the repository root with Docker running:

```powershell
docker build --pull -t ai-code-review-backend .
docker run --rm --init --name code-review-local -p 8001:8000 --memory=1g --cpus=1 ai-code-review-backend
```

In another terminal, `curl.exe http://127.0.0.1:8001/` should return the existing
health message. No AI key is needed. Stop the container with Ctrl+C. To allow
local Vite access during a container test, explicitly pass `-e APP_ENV=development`
and `-e CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173`, then configure
Vite's development `VITE_API_URL=http://127.0.0.1:8001`. The image contains no `.env`.

## Deploy step by step on Render

No deployment, commit, or push was performed as part of this preparation.
When you decide to deploy, make the reviewed changes available on the branch
you choose to connect. Render cannot build uncommitted local changes from GitHub.

### 1. Create the backend

1. In Render, select **New → Web Service** and connect the repository/branch.
2. Select **Docker** as the runtime. Leave Root Directory at the repository
   root. Set Dockerfile Path to `./Dockerfile` and Docker Build Context to `.`.
3. Leave the Docker Command override empty; the image starts `python -m backend`.
4. Set Health Check Path to `/`. Select your region and a paid instance size.
5. Set `APP_ENV=production` and `LIMIT_CONCURRENCY=8`. Initially leave
   `CORS_ORIGINS` unset; it will be configured after creating the frontend.
   Let Render supply `PORT`; do not copy the local `.env` wholesale.
6. Initially leave `OPENAI_API_KEY` unset for a static-analysis smoke test.
   Add it later as a backend secret when access protection is in place.
   Never supply it as a Docker build argument or frontend environment variable.
7. Deploy. Open the assigned public HTTPS URL at `/` and confirm the health
   message. Record this URL for the frontend.

The Dockerfile installs only `requirements.txt`. Development/test packages are
in `requirements-dev.txt`. The allowlist in `.dockerignore` excludes Git history,
local environments, secrets, tests, frontend assets, and screenshots from the
backend build context. No production hostname is committed to source code.

### 2. Create the frontend

1. Select **New → Static Site** and connect the same repository/branch.
2. Set Root Directory to `frontend`.
3. Set Build Command to `npm ci --include=dev && npm run build`.
4. Set Publish Directory to `dist` (relative to the frontend root).
5. Set `VITE_API_URL` to the backend's assigned public HTTPS URL.
6. Set `SKIP_INSTALL_DEPS=true` so the explicit `npm ci` command controls
   installation. The repository's Node 22 configuration avoids relying on the
   hosting platform's changing default; remove conflicting `NODE_VERSION` overrides.
7. Deploy and record the frontend's HTTPS origin. The current app uses one page
   and has no client-side router, so no SPA rewrite rule is necessary.

### 3. Connect the two services

1. On the backend, set `CORS_ORIGINS` to the exact frontend origin, for example
   the assigned `https://…onrender.com` origin, without a path. Save/redeploy.
2. Reload the frontend and submit a small public Python repository.
3. Confirm health score, issue counts, filenames, top issues, and filters work.
4. Switch to Code Diff Review and compare `x = 1` with `x = 1` followed by
   `print(x)` on a second line. Expect a print finding at line 2.
5. Confirm invalid/non-GitHub URLs produce a clear error. Check backend logs for
   cleanup failures and resource usage; avoid logging submitted source code.
6. After applying access/rate controls, optionally add `OPENAI_API_KEY` to the
   backend and request one AI review. This live check can incur API charges;
   automated tests always mock OpenAI instead.

For custom domains, update `CORS_ORIGINS` on the backend and, if the backend
domain changes, rebuild the frontend with the new `VITE_API_URL`. Do not allow
wildcard preview domains. Add only explicitly trusted origins.

## Operations and remaining limits

- The existing `/` health endpoint checks app availability, not OpenAI credits,
  GitHub connectivity, or analysis capacity. Alert on failed deployments and 5xxs.
- Render handles public HTTPS. Keep the backend port behind the hosting proxy.
  Uvicorn's proxy-header trust is not widened by this code; only configure
  `FORWARDED_ALLOW_IPS` if you know the trusted proxy addresses/topology.
- Cloning can take up to 60 seconds, followed by AST analysis and optional AI
  calls. Avoid short-timeout serverless functions for this backend. If using a
  different reverse proxy, configure request timeouts for these long operations.
- Resource limits are polling safeguards. Host-enforced CPU/memory/disk limits,
  request-body limits, authentication, rate limiting, and isolated workers remain
  necessary for an unrestricted public service. The server concurrency cap is
  only one layer and does not replace those controls.
- Do not mount persistent storage for temporary clones. Rebuild images regularly
  for OS/Python security updates and update pinned dependencies deliberately.
- No container build or live hosting deployment can be claimed until Docker
  and the provider have successfully built these files in your environment.

Additional references: [Render web services](https://render.com/docs/web-services)
and [Node version configuration](https://render.com/docs/node-version).
