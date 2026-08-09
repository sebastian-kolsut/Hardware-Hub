# Hardware Hub

A hardware inventory and rental platform: a Django REST backend with
token-authenticated roles (admin/regular user), a rent/return workflow, an
import pipeline that flags data anomalies for review, and Gemini-powered
semantic search over the catalog — fronted by a Vue 3 + Vite dashboard.

## Stack

- **Backend**: Django 6, Django REST Framework, SQLite, [uv](https://docs.astral.sh/uv/) for dependency management, [google-genai](https://pypi.org/project/google-genai/) for embeddings
- **Frontend**: Vue 3, Vite

## Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/) (manages Python 3.12 automatically)
- Node.js 18+ and npm
- Docker and Docker Compose (only if you want to run via containers instead of locally)
- A [Gemini API key](https://ai.google.dev/) if you want semantic search to actually return ranked results (everything else works without one)

## Setup Instructions

### 1. Clone and configure environment variables

```bash
git clone <repo-url> hardware-hub
cd hardware-hub
cp .env.example .env
```

Generate a real Django secret key and paste it into `.env` as `DJANGO_SECRET_KEY`:

```bash
cd backend
uv run python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
cd ..
```

Also set `GEMINI_API_KEY` in `.env` to a real key (semantic search will silently
report failures per-item without one — see below). The rest of the defaults in
`.env.example` work for local development out of the box.

This single `.env` file at the repo root is shared by both the backend and
the frontend (via Docker Compose `env_file`, or via `django-environ` reading
it directly in local dev).

### 2. Run with Docker Compose (recommended)

From the repo root:

```bash
docker compose up --build
```

This starts:

- **backend** on [http://localhost:8000](http://localhost:8000)
- **frontend** on [http://localhost:5173](http://localhost:5173)

In another terminal, run the one-time setup — **in this order**, since
`generate_embeddings` needs rows to already exist and `import_hardware`
bypasses the normal per-row embedding step (see "Shortcuts & Hacks" below):

```bash
docker compose exec backend uv run manage.py migrate
docker compose exec backend uv run manage.py createsuperuser
docker compose exec backend uv run manage.py import_hardware
docker compose exec backend uv run manage.py generate_embeddings
```

Then open [http://localhost:5173](http://localhost:5173) and log in with the
superuser you just created (there's no public registration — admins create
every other account from the dashboard's "Create user account" form).

### 3. Run locally without Docker

**Backend:**

```bash
cd backend
uv sync
uv run manage.py migrate
uv run manage.py createsuperuser
uv run manage.py import_hardware       # loads backend/../data.json into the database
uv run manage.py generate_embeddings   # backfills embeddings for the rows import_hardware just created
uv run manage.py runserver
```

**Frontend** (in a separate terminal):

```bash
cd frontend
npm install
npm run dev
```

The app is now available at [http://localhost:5173](http://localhost:5173) and
talks to the backend at the URL set by `VITE_API_URL` in `.env`.

## API overview

All endpoints below except `/api/ping/` and `/api/auth/login/` require an
`Authorization: Token <key>` header (obtained from `/api/auth/login/`).

| Endpoint | Notes |
| --- | --- |
| `GET /api/ping/` | Health check, no auth. |
| `POST /api/auth/login/`, `/logout/`, `GET /me/` | Token auth lifecycle. |
| `POST /api/auth/users/` | Admin-only account creation. |
| `GET /api/hardware/` | List. Regular users never see `needs_review=True` rows; admins see everything, flagged first. |
| `GET /api/hardware/?mine=true` | Scoped to items the caller has rented, regardless of role. |
| `GET /api/hardware/?q=<text>` | Semantic search — ranks the same visibility-filtered set by cosine similarity; 503 if the embedding API call fails. |
| `POST /api/hardware/` , `PATCH`/`DELETE /api/hardware/<id>/` | Admin-only create/edit/delete. |
| `POST /api/hardware/<id>/rent/` , `/return/` | Any authenticated user; return is restricted to the renter or an admin. |
| `/admin/` | Django admin — every record, flagged or not. |

## Data import notes

`import_hardware` reads `data.json` (JSON array of records) and loads it into
the `Hardware` table. Records with issues — duplicate ids, missing/invalid
purchase dates, dates in the future, unrecognized statuses, or any mention of
"unknown" — are imported anyway but flagged with `needs_review=True` and a
`review_notes` explanation, visible both in the Django admin and (for admins)
directly in the dashboard.

Useful flags:

```bash
uv run manage.py import_hardware --dry-run        # report anomalies without writing to the DB
uv run manage.py import_hardware --file path.json  # import from a different file
```

`import_hardware` uses `bulk_create`, which skips each row's `save()` — and
therefore skips embedding computation. Run `generate_embeddings` afterward to
backfill them:

```bash
uv run manage.py generate_embeddings          # only rows missing an embedding
uv run manage.py generate_embeddings --force  # recompute every row's embedding
```

## Environment variables

Defined in `.env` (see `.env.example`):

| Variable | Description |
| --- | --- |
| `DJANGO_SECRET_KEY` | Django cryptographic signing key. Generate your own; never reuse across environments. |
| `DJANGO_DEBUG` | `True`/`False`. Keep `True` for local dev only. |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hostnames the backend will serve. |
| `CORS_ALLOWED_ORIGINS` | Comma-separated origins allowed to call the API (the frontend's URL). |
| `GEMINI_API_KEY` | Used to compute item and query embeddings for semantic search. Without a valid key, embedding computation fails per-item (logged, non-fatal) and `?q=` returns a 503. |
| `VITE_API_URL` | URL the browser uses to reach the backend. |

## Running tests

```bash
cd backend
uv run manage.py test
```

The suite mocks the Gemini API everywhere (`hardware.embeddings.embed_text`)
— it never makes a real network call or depends on a valid `GEMINI_API_KEY`.
There is currently no automated frontend test suite (see "Partial/Missing" below).

## Implementation Status & Trade-offs

### ✅ Fully Implemented

**Management Engine**
- Token-based login/logout with session restore on page load (validates the
  stored token against `/api/auth/me/` rather than trusting it blindly).
- Two roles via `User.is_staff` — a single `IsAdminUser` permission class
  gates every admin-only view/action, no per-view hand-rolled checks.
- Hardware dashboard: client-side keyword search, status filter, and
  sortable columns; admin-only inline row actions (edit, send-to-repair,
  delete) plus "Add hardware" / "Create user account" forms.
- `needs_review` triage is a first-class part of the admin dashboard, not
  just the Django admin: flagged rows are surfaced (sorted first from the
  API), visually highlighted with a "Needs review" badge and tooltip
  (`review_notes`), and an "Approve" action clears the flag — instantly
  making the item visible to regular users, since visibility is derived
  live from `needs_review`, not cached.

**Rental Engine**
- Rent (`POST /api/hardware/<id>/rent/`): rejects anything not `available`
  with a specific reason (already rented / in repair / flagged for review),
  re-checking `needs_review` itself rather than trusting the caller went
  through a filtered list first.
- Return (`POST /api/hardware/<id>/return/`): 403 for anyone but the current
  renter or an admin; 409 (not a crash) if the item isn't rented at all.
- Visibility is asymmetric by design: every authenticated user can tell
  whether *they* are the renter (`rented_by_me`), but the renter's identity
  (`rented_by`) is only included in the API response for the renter
  themselves or an admin — enforced in the serializer, not hidden client-side.
- "My Rentals" — a sidebar-driven view scoped via `?mine=true`, which
  overrides the normal admin-sees-everything visibility rule (an admin's
  `?mine=true` is exactly as narrow as anyone else's).

**Data Import & Audit Pipeline**
- `import_hardware` flags, per row: missing name, duplicate source id,
  missing/unparseable/inconsistent/future purchase dates, unrecognized
  status, and any mention of "unknown" — imported anyway (never silently
  dropped) with `needs_review=True` and a human-readable `review_notes`.
- `--dry-run` and `--file` flags; re-running replaces the dataset entirely
  (matches the take-home's "re-import" semantics).

**AI-Native Semantic Search**
- Each item's embedding (name + brand + all `extra` values — e.g. a
  "Battery swelling" note counts) is computed once via the Gemini
  embedding API and stored on the row, not recomputed per search.
- `GET /api/hardware/?q=<text>` costs exactly one Gemini call (the query
  text), then ranks every item that has a stored embedding by cosine
  similarity computed in Python — no threshold, everything searchable is
  always returned, just reordered.
- Respects the exact same `needs_review`/role visibility rules as the plain
  list (verified by test — a regular user's search cannot surface a
  flagged item even if it would otherwise rank first).
- A distinct "AI search" box in the dashboard (separate from the keyword
  filter) renders results in backend rank order with no client-side
  re-sorting, with its own loading state and a 503 error message instead
  of failing silently onto stale data.

### ⚡ Shortcuts & "Hacks"

- **No dedicated vector database.** Embeddings are a plain `JSONField`;
  `?q=` pulls every embedded row into Python and computes cosine similarity
  in a loop. *Why:* fine at a dozen-ish items, and avoids standing up/
  operating a whole extra service for a take-home. *Future:* pgvector (if
  staying on Postgres) or a dedicated store (Qdrant/Chroma) with an ANN
  index once linear comparison stops being free.
- **DRF `TokenAuthentication` instead of JWT.** Opaque, stateful tokens
  stored as-is in the DB. *Why:* trivial to implement and revoke (delete
  the row, done) versus JWT's refresh-token machinery. *Trade-off worth
  knowing:* the token never expires on its own and isn't hashed at rest —
  a DB leak hands over live credentials, not just password hashes.
  *Future:* short-lived JWT + refresh, or `django-rest-knox` for expiring
  tokens without giving up the simple opaque-token model.
- **SQLite instead of a production database.** *Why:* zero setup, one file,
  perfect for a take-home. *Future:* Postgres — needed anyway for pgvector
  above, and for real concurrent-write behavior.
- **Auth token in `localStorage`.** *Why:* the only way `restoreSession()`
  can survive a page refresh without a cookie-based backend redesign, and
  this app renders no unescaped/untrusted content (no `v-html`), so there's
  currently no XSS vector to steal it through. *Trade-off:* any future XSS
  hole would expose it directly, and — same root cause as the token point
  above — a stolen token doesn't expire. *Future:* `httpOnly` cookie-based
  sessions (needs CSRF handling) if the app ever renders user-supplied HTML.
- **Embeddings computed synchronously inside `save()`.** Creating or
  editing a hardware record makes the HTTP request wait on a live Gemini
  API call. *Why:* simplest possible correct implementation — no task
  queue, no worker process, no eventual-consistency window to reason
  about, and failures are caught and logged rather than blocking the save.
  *Future:* push the embedding call to a background task (Celery/RQ/
  Django-Q) so a slow or down embedding API can't add latency to admin
  edits.
- **No pagination on `/api/hardware/`.** Every request returns the entire
  table. *Why:* trivial at the current catalog size, and semantic search
  needs the full embedded set in memory regardless. *Future:* real
  pagination once the catalog is large enough that this matters — which
  also forces the vector-database question above, since "page through
  results ranked by similarity" doesn't work against an in-memory sort.
- **No rate limiting anywhere** (login attempts, or `?q=` — which spends a
  real, metered Gemini API call per request). *Why:* not needed to
  demonstrate the feature set. *Future:* DRF's built-in throttle classes
  are a few lines away — cheap to add before this is exposed beyond a demo.
- **Dev servers in Docker, not a production build.** Both containers run
  `manage.py runserver` and `vite dev` (see the Dockerfiles), and
  `DJANGO_DEBUG=True` by default. *Why:* this is what you want for local
  iteration, and it's what the task called for. *Future:* gunicorn/uvicorn
  behind a real ASGI/WSGI setup, `vite build` served as static assets,
  `DEBUG=False` with a real `ALLOWED_HOSTS`.

### ⚠️ Partial/Missing

- **No rental history.** `Hardware.rented_by`/`rented_at` track only the
  *current* renter — returning an item wipes the record of who had it
  before. There's no log of past rentals, so "My Rentals" can only ever
  show what's rented right now, never a history. (`rented_at` itself is
  also currently write-only in practice — nothing displays how long an
  item has been checked out, and there's no overdue concept at all.)
- **No pagination** on the hardware list (see Shortcuts above — listed
  again here because it's a real functional gap, not just a scaling one:
  the frontend has no concept of "next page" at all).
- **No bulk actions for `needs_review` items** — approving is one row at a
  time, in both the Django admin (no custom admin `actions` defined) and
  the Vue dashboard. A queue of a dozen flagged imports means a dozen
  individual clicks.
- **No password reset / account recovery.** Admins can create accounts but
  there's no endpoint to reset an existing user's password — a locked-out
  user has no self-service path, and neither does an admin on their behalf
  short of the Django admin's password-change form.
- **No automated frontend tests.** The backend has 56 tests covering
  permissions, visibility rules, and the rent/return/search state machines;
  the Vue side has none (no Vitest/Cypress setup at all), so regressions in
  the dashboard's client-side logic (sorting, the AI-search mode switch,
  cross-list row sync) rely entirely on manual verification.

### 🔮 Next Steps (The 24h Roadmap)

1. **Add a proper vector database (pgvector or similar)** to replace the
   in-memory cosine similarity comparison, for when the catalog scales
   past a trivial size.
2. **Add a short product description field** (possibly AI-generated at
   creation time) that gets included in the embedding text, to improve
   semantic search recall beyond just name + brand.
3. **Add rental history** — a proper log of an item's past renters (not
   just the current one) and a per-user view of what they've rented over
   time. Unlike the other two priorities, which improve an existing
   feature, this is a capability that's completely absent right now:
   returning an item permanently erases the record of who had it before,
   so there's no way to answer "who has used this laptop" or "what has
   this person rented" — core things a rental system is expected to
   track. It also needs a schema change (a real rental-record table
   instead of two fields on `Hardware`), which is better done now, before
   more features get built on top of the current "current state only"
   model, than later as a disruptive migration.
