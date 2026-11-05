# Kontiq

Kontiq is a local-first Django workspace for organizing business context, planning SEO content, generating drafts with OpenAI, and keeping editable, versioned exports on the local filesystem.

## Current status

The roadmap MVP is implemented. Authenticated users can:

- create isolated projects with business context, links, and private TXT/PDF/DOCX references;
- define content types, restricted prompt templates, and project-specific prompt overrides;
- create individual or bulk content tasks, schedule them, filter them, and queue generation;
- generate through a provider-neutral service and OpenAI adapter outside HTTP requests;
- prevent duplicate execution with durable database tokens and explicit state transitions;
- dispatch due work through Celery Beat and recover stale locks;
- edit generated content while retaining immutable versions;
- download escaped HTML and locally generated DOCX files through ownership-checked views;
- review database-derived dashboard totals, queue state, provider readiness, and safe activity history.

Structural output validation does not imply factual verification. Review generated content before publication.

## Technology

- Python 3.10+
- Django 5.2 LTS
- SQLite locally, with PostgreSQL-compatible ORM usage
- Celery 5.6 and Redis
- OpenAI Python SDK
- `python-docx` and `pypdf`
- Django templates with locally vendored Bootstrap 5.3.8

See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for application ownership, data relationships, and workflow boundaries.

## Quick start

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open <http://127.0.0.1:8000/> and sign in. Django admin is at <http://127.0.0.1:8000/admin/>.

The web UI works without Redis. AI generation and scheduled dispatch require Redis plus worker processes.

## Environment configuration

| Variable | Purpose | Local default |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | Session and signing secret | Unsafe development value in debug mode |
| `DJANGO_DEBUG` | Development mode | `True` |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hosts | `localhost,127.0.0.1` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | HTTPS proxy origins | Empty |
| `DJANGO_TIME_ZONE` | Application/Celery timezone | `Asia/Kolkata` |
| `DATABASE_URL` | Django database URL | `sqlite:///db.sqlite3` |
| `REDIS_URL` | Celery broker/result backend | `redis://127.0.0.1:6379/0` |
| `CELERY_TASK_ALWAYS_EAGER` | Inline execution for isolated testing only | `False` |
| `OPENAI_API_KEY` | Server-side OpenAI credential | Empty |
| `OPENAI_MODEL` | OpenAI Responses API model | Empty |
| `AI_MAX_RETRIES` | Bounded structural correction attempts | `2` |
| `AI_TASK_MAX_ATTEMPTS` | Maximum durable worker attempts | `3` |
| `AI_TIMEOUT_SECONDS` | Provider request timeout | `90` |
| `AI_MAX_OUTPUT_TOKENS` | Provider output cap | `8000` |
| `MAX_REFERENCE_UPLOAD_MB` | Per-reference upload limit | `10` |

Generation remains honestly disabled until both `OPENAI_API_KEY` and `OPENAI_MODEL` are set. Credentials are never displayed, stored in application models, included in activity metadata, or sent to templates.

For production, set a strong secret, disable debug mode, specify exact hosts/origins, enable HTTPS cookie settings, and use PostgreSQL before running concurrent workers.

## Redis and background processes

On Debian/Ubuntu:

```bash
sudo apt install redis-server
sudo systemctl enable --now redis-server
redis-cli ping
```

Run each process in a separate terminal with the virtual environment active:

```bash
python manage.py runserver
celery -A config worker --loglevel=INFO
celery -A config beat --loglevel=INFO
```

Beat invokes the due-work dispatcher once per minute. The relational database remains authoritative for schedules, statuses, locks, and content. Run only one Beat process per deployment.

## Product workflow

1. Create a project and add audience, voice, instructions, avoidance rules, links, and optional references.
2. Create a content type. Kontiq also creates its default restricted prompt.
3. Edit the default prompt or add a project override using only the variables shown in Prompt Manager.
4. Create a content task or use bulk creation. Optionally schedule it for a future time.
5. Use **Generate** or let Beat dispatch a due task. The request reserves a durable lock and returns after queueing.
6. The worker assembles scoped context, invokes OpenAI, parses JSON, validates structure/length/keyword presence, and performs bounded correction attempts.
7. Completed content appears in Content Library. Edits preserve the previous state as an immutable version.
8. Export through the authorized HTML or DOCX download views.

Reference text and model output are treated as untrusted. Prompt rendering performs restricted scalar substitution, HTML export escapes content, uploads validate extension/size/signature, and private files never rely on an obscure media URL as authorization.

## Tests and checks

```bash
python manage.py check
python manage.py test
python manage.py makemigrations --check --dry-run
```

The suite covers authentication, tenant isolation, upload validation, prompt-variable validation, task creation/bulk input, provider configuration failure, generation persistence and idempotency, due dispatch, stale-lock recovery, version preservation, escaped/private downloads, navigation, and primary-page rendering. Provider calls are mocked and tests never consume paid APIs.

## Storage

```text
media/
├── project_references/<project-slug>/<uuid>-<safe-name>.<ext>
└── generated_docs/<project-slug>/<task-id>-<slug>-v<version>.docx
```

Database records store relative paths. Project/task/reference deletion is explicit and removes the corresponding stored artifacts. Production deployments must serve source static files separately and keep private media behind the authenticated Django download views.

Collect deployment static files with:

```bash
python manage.py collectstatic
```

## Troubleshooting

- **`ModuleNotFoundError`**: activate `.venv` and reinstall `requirements.txt`.
- **No application tables**: run `python manage.py migrate`.
- **Generate says setup is required**: set both OpenAI variables and restart web/worker processes.
- **Queueing fails**: verify `redis-cli ping`, `REDIS_URL`, and the Celery worker.
- **Scheduled work stays scheduled**: enable the project policy, run Beat, and verify provider/Redis settings.
- **A task remains processing after a worker crash**: the periodic dispatcher recovers locks older than 30 minutes; the task becomes failed and can be queued again.
- **SQLite lock errors**: use a single local worker or migrate to PostgreSQL.
- **Static assets missing**: check `DJANGO_DEBUG` locally or run `collectstatic` and configure the production web server.

## Scope and future hardening

The local-first MVP is complete. Production-scale additions intentionally not claimed here include organization-level multi-tenancy, encrypted database-backed provider credentials, malware scanning, semantic reference retrieval, cost quotas, factual verification, and multi-provider adapters beyond OpenAI.
