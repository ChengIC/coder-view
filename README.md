# coder-view

Web app to evaluate an entire codebase using a FastAPI backend with an OpenAI-compatible API and store the JSON report in Supabase. The frontend is React (TypeScript, Vite).

## Tech Stack
- Frontend: React + TypeScript (Vite)
- Backend: FastAPI (Python)
- LLM: OpenAI-compatible API hosted on company servers (configurable `LLM_API_BASE`)
- Storage: Supabase (table `reports`)

## Project Structure
- `server/` – FastAPI API, evaluator, Supabase integration
- `web/` – Vite React frontend

## Environment Variables
Create `server/.env` based on `server/.env.example`:

```
LLM_API_BASE=https://your-company-llm.example.com
LLM_API_KEY=your_llm_api_key
LLM_MODEL=gpt-4o-mini

SUPABASE_URL=https://your-supabase-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
```

Frontend can point to the backend via `VITE_API_URL` (default `http://localhost:8000`). If desired, create `web/.env`:

```
VITE_API_URL=http://localhost:8000
```

## Supabase Table
Create a `reports` table with JSON columns (or text for summary):
- `run_id` (text)
- `project_name` (text)
- `metrics` (json)
- `summary` (json or text)
- `created_at` (timestamp default now())

## Setup

Backend (FastAPI):
1. Install Python deps: `python3 -m pip install -r server/requirements.txt`
2. CD into `server/`
2. Run dev server: `uvicorn main:app --reload --port 8000`

Frontend (React + Vite):
1. From `web/`: `sudo npm install` (if needed)
2. Run dev server: `sudo npm run dev`

## Deployment (Docker)

This repo ships with production-ready Docker images and a compose file to deploy the full system (API + Web):

- API: FastAPI served by `uvicorn` on port `8000`
- Web: React + Vite built to static assets and served by Nginx on port `8080`

### 1) Prepare environment

- Copy `server/.env.example` to `server/.env` and fill in the values:

```
LLM_API_BASE=https://your-company-llm.example.com
LLM_API_KEY=your_llm_api_key
LLM_MODEL=gpt-4o-mini

SUPABASE_URL=https://your-supabase-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
SUPABASE_ANON_KEY=your_anon_key_if_needed
SUPABASE_JWT_SECRET=your_jwt_secret_from_supabase_settings
```

- Optionally set frontend build-time variables via a top-level `.env` file or your shell when running compose:

```
# Used at build-time for the web image
VITE_API_URL=http://localhost:8000
VITE_SUPABASE_URL=https://your-supabase-project.supabase.co
VITE_SUPABASE_ANON_KEY=your_anon_key
```

If not provided, the frontend defaults to `http://localhost:8000` for the API.

### 2) Build and run

From the repo root:

```
docker compose up -d --build
```

This starts:
- `api` on `http://localhost:8000`
- `web` on `http://localhost:8080`

### 3) Health checks

- API health: `curl http://localhost:8000/health`
- Web served: open `http://localhost:8080/`

### Notes

- The frontend is a static SPA served by Nginx with client-side routing (`try_files /index.html`).
- For production, set `VITE_API_URL` to your public API endpoint (e.g., `https://api.example.com`).
- Authentication uses Supabase JWT verification; set `SUPABASE_JWT_SECRET` in `server/.env`.
- CORS: set `ALLOWED_ORIGINS` in `server/.env` (comma-separated) for your frontend origin(s). Defaults include `http://localhost:5173` and `http://localhost:8080`.
- Logs are written to `server/logs/app.log` inside the container; consider mounting a volume if you need persistence.

## Usage
1. Zip your codebase parent directory (exclude heavy folders like `node_modules` if possible).
2. Open `http://localhost:5173`.
3. Upload the `.zip`. The backend evaluates:
   - Readability: README/docstrings/comments
   - Reusability: duplicate logic detection
   - Robustness: tests, type hints, try/except
   - Performance: simple heuristics for SQL injection risk and risky calls
4. Backend stores the report JSON in Supabase (if env configured) and returns it to the frontend for display.

## Notes
- LLM summary is optional; if `LLM_API_BASE`/`LLM_API_KEY` are not set, the app still produces heuristic metrics.
- The duplicate detection is heuristic (normalized content hashing) and may produce false positives/negatives.
- Avoid uploading sensitive code without proper approvals.
