# Hardware Hub

A hardware inventory dashboard: a Django REST backend that imports and serves
hardware records (flagging anomalies for review), and a Vue 3 + Vite frontend
that displays them with sorting and filtering.

## Stack

- **Backend**: Django 6, Django REST Framework, SQLite, [uv](https://docs.astral.sh/uv/) for dependency management
- **Frontend**: Vue 3, Vite

## Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/) (manages Python 3.12 automatically)
- Node.js 18+ and npm
- Docker and Docker Compose (only if you want to run via containers instead of locally)

## 1. Configure environment variables

Copy the example env file and generate a real Django secret key:

```bash
cp .env.example .env

cd backend
uv run python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Paste the generated value into `.env` as `DJANGO_SECRET_KEY`. The rest of the
defaults in `.env.example` work for local development out of the box.

This single `.env` file at the repo root is shared by both the backend and
the frontend (via Docker Compose `env_file`, or via `django-environ` reading
it directly in local dev).

## 2. Run with Docker Compose (recommended)

From the repo root:

```bash
docker compose up --build
```

This starts:

- **backend** on [http://localhost:8000](http://localhost:8000)
- **frontend** on [http://localhost:5173](http://localhost:5173)

The backend container mounts `data.json` from the repo root. To run
migrations and import the sample hardware data, in another terminal:

```bash
docker compose exec backend uv run manage.py migrate
docker compose exec backend uv run manage.py import_hardware
```

Then open [http://localhost:5173](http://localhost:5173) in your browser.

## 3. Run locally without Docker

### Backend

```bash
cd backend
uv sync
uv run manage.py migrate
uv run manage.py import_hardware   # loads backend/../data.json into the database
uv run manage.py createsuperuser   # optional, for /admin/ access
uv run manage.py runserver
```

The API is now available at [http://localhost:8000](http://localhost:8000):

- `GET /api/ping/` — health check
- `GET /api/hardware/` — list hardware records
- `/admin/` — Django admin (flagged/anomalous records are visible here)

### Frontend

In a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

The app is now available at [http://localhost:5173](http://localhost:5173) and
talks to the backend at the URL set by `VITE_API_URL` in `.env`.

## Data import notes

`import_hardware` reads `data.json` (JSON array of records) and loads it into
the `Hardware` table. Records with issues — duplicate ids, missing/invalid
purchase dates, dates in the future, unrecognized statuses, or any mention of
"unknown" — are imported anyway but flagged with `needs_review=True` and a
`review_notes` explanation, visible in the Django admin.

Useful flags:

```bash
uv run manage.py import_hardware --dry-run        # report anomalies without writing to the DB
uv run manage.py import_hardware --file path.json  # import from a different file
```

## Environment variables

Defined in `.env` (see `.env.example`):

| Variable | Description |
| --- | --- |
| `DJANGO_SECRET_KEY` | Django cryptographic signing key. Generate your own; never reuse across environments. |
| `DJANGO_DEBUG` | `True`/`False`. Keep `True` for local dev only. |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hostnames the backend will serve. |
| `CORS_ALLOWED_ORIGINS` | Comma-separated origins allowed to call the API (the frontend's URL). |
| `VITE_API_URL` | URL the browser uses to reach the backend. |

## Running tests

```bash
cd backend
uv run manage.py test
```
