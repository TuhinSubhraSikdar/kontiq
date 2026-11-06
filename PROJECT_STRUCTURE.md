# Kontiq Architecture and Project Structure

This document is the architecture contract for the implemented local-first MVP.

## Principles

- The relational database is authoritative for content, schedules, statuses, and locks.
- Redis is transport and coordination infrastructure, never durable business storage.
- Every user-owned query is scoped through the authenticated owner boundary.
- HTTP views handle request/response concerns; forms validate browser input; services own workflows.
- Celery tasks are thin entry points into idempotent services.
- AI provider calls stay inside `apps/ai_engine/providers`.
- Uploaded and generated data is untrusted and private until an authorized view serves it.
- SQLite supports single-machine development; PostgreSQL is required for meaningful worker concurrency.

## Implemented tree

```text
Kontiq/
├── config/                 Settings, root URLs, WSGI/ASGI, Celery bootstrap
├── apps/
│   ├── core/               Shared authenticated foundation route
│   ├── dashboard/          Database totals and live readiness
│   ├── projects/           Projects, links, references, extraction, private downloads
│   ├── content_types/      User-owned content format definitions
│   ├── prompts/            Restricted templates, overrides, rendering, preview
│   ├── content_tasks/      Spreadsheet queue, CSV/bulk creation, briefs, filters, schedules, durable state
│   ├── ai_engine/          Assembly, provider adapter, parsing, validation, orchestration
│   ├── scheduler/          Per-project policy, due dispatch, stale-lock recovery
│   ├── content_library/    Generated content, versions, editing, HTML/DOCX exports
│   └── activity_logs/      Safe append-oriented operational events
├── templates/              Base shell, components, and namespaced domain templates
├── static/                 Design system, enhancement JS, favicon, vendored Bootstrap
├── media/                  Runtime-only private references and documents
├── tests/                  Cross-application render/integration tests
├── manage.py
├── requirements.txt
├── .env.example
└── README.md
```

Each model-owning app has an initial migration. App-local tests cover domain behavior; root tests cover the assembled application.

## Models and ownership

```text
User
 ├── Project (owner + slug unique)
 │    ├── ProjectLink
 │    ├── ProjectReference
 │    ├── PromptTemplate overrides
 │    ├── ScheduleConfiguration (one-to-one, created automatically)
 │    ├── ContentTask
 │    │    ├── ActivityLog
 │    │    └── GeneratedContent (one-to-one)
 │    │         └── GeneratedContentVersion
 │    └── ActivityLog
 ├── ContentType (owner + slug unique)
 │    └── PromptTemplate defaults/overrides
 └── ActivityLog

Global AI configuration
 ├── AIProviderConfiguration (encrypted credential + provider/model/endpoint)
 └── AIProviderSelection (singleton active configuration pointer)
```

`ContentType` also owns presentation metadata (category, icon, color), optional planning-field names, and a favorite flag. `PromptTemplate` stores editor metadata, a favorite flag, and its current version number; `PromptVersion` keeps immutable pre-edit snapshots for explicit restore actions.

`Project.owner` and `ContentType.owner` are required. Descendant access always scopes through those roots. IDs alone are never authorization.

### Projects and files

`Project` stores normalized business context without coupling it to provider code. `ProjectLink` categorizes approved URLs. `ProjectReference` records a safe relative path, original name, MIME label, size, SHA-256 checksum, extraction state, extracted text, and safe extraction error.

Reference forms enforce size and `.txt`/`.pdf`/`.docx` extensions, verify PDF/DOCX signatures, normalize storage names, and reject per-project duplicates. Extraction uses UTF-8, `pypdf`, or `python-docx`. Downloads require authentication and ownership. Explicit deletion removes database records and stored files.

### Content types and prompts

Content types are user-owned so one account cannot discover another account’s formats. Creating one also creates a default prompt. A prompt may be a per-content-type default or a project override, enforced by conditional unique constraints.

Every new account receives six idempotent starter types with default prompts: Web 2.0, Blog Posting, PR Submission, Contextual, LLM Blog (Short Blog), and Others. A data migration adds any missing starters for existing accounts without overwriting matching user-owned records or later customizations.

Prompt rendering recognizes a documented `{{ variable }}` syntax with a fixed allowlist. It does not evaluate Django, Jinja, Python, or arbitrary expressions. Unknown variables fail form validation.

The Content Types screen is the primary prompt-management entry point. Each type opens a dedicated workspace for its default and project-scoped prompts. The Prompt Library provides cross-workspace search and filtering, while prompt edits preserve the previous template as a restorable version.

### Task state and idempotency

Task states are:

```text
draft/scheduled → queued → processing → completed
                               └──────→ failed
failed/completed ──manual Generate──→ queued
```

Queue reservation uses a transaction and row lock, stores a UUID execution token and lock time, and then publishes a short Celery message. A worker may process only a queued task whose persisted token matches. Duplicate/redelivered messages therefore cannot produce a second content record. Provider/network work runs outside database transactions. Completion and failure use short locked transitions.

If broker publication fails, the reservation becomes a visible failed task with a safe error. Provider failures are rescheduled in the database using the project retry delay until `AI_TASK_MAX_ATTEMPTS` is reached. Stale queued/processing locks older than 30 minutes are recovered to failed by the periodic dispatcher. Users may explicitly queue failed tasks again.

## Generation stages

```text
manual action or due dispatcher
          │
          ▼
transactional queue reservation
          │
          ▼
thin Celery task
          │
          ▼
generation service
  1. collect authorized project context (bounded reference characters)
  2. select project override, default prompt, or safe fallback
  3. perform restricted variable substitution
  4. load the active encrypted provider configuration (or OpenAI environment fallback)
  5. invoke the provider adapter request
  6. parse required JSON fields
  7. validate title/body/slug/meta length/word count/keyword
  8. request bounded structural correction when needed
  9. atomically persist content/version and complete task
 10. append safe activity metadata
```

The provider contract is represented by `GenerationRequest` and `GenerationResult`. `OpenAIProvider` translates it to the OpenAI Responses API. `OpenAICompatibleProvider` uses the compatible chat-completions surface exposed by Anthropic, Gemini, Groq, OpenRouter, and administrator-supplied compatible HTTPS endpoints. Both retain only the provider name, model, response identifier, and safe usage metadata. Assembled prompts and raw responses are not logged or persisted.

Validation establishes format compliance, not factual truth.

## Scheduling

Every project receives a one-to-one `ScheduleConfiguration`. It controls whether due work is dispatched and caps active tasks per project. Celery Beat calls `kontiq.dispatch_due_tasks` once per minute. The dispatcher queries due database rows and uses the same queue service as manual generation; it does not create long-lived ETA messages.

Only one Beat scheduler should run for a deployment. SQLite users should keep worker concurrency low.

## Content and versions

`GeneratedContent` is one-to-one with its task and duplicates the project/content-type references deliberately for efficient ownership and library queries. Provider/model/response ID/usage metadata remain attached to the current result.

The first generated result creates version 1. Before an edit or regeneration replacement, the service stores an immutable snapshot. Restore also snapshots the current state first. Edited body text is plain untrusted text; preview uses Django escaping. HTML export escapes every field and converts only recognized plain-text heading prefixes. DOCX rendering uses `python-docx` and stores the artifact under `media/generated_docs`.

## Activity and privacy

Activity records include a user, optional project/task, an event type, a short summary, and deliberately small safe JSON metadata. Callers must not include credentials, prompts, raw provider payloads, or unnecessary customer content. Activity records cascade with their owning project/task rather than becoming orphaned content storage.

## HTTP and templates

All domain routes use Django authentication. Object fetches include owner filters. State-changing actions use POST and CSRF protection; deletion requires a dedicated confirmation page. The sidebar exposes only working routes.

Templates extend a shared responsive product shell with collapsible dark navigation, light and dark workspace themes, global prompt search, semantic tables, labels, focus styles, status badges, and keyboard-usable controls. Bootstrap assets are local so the UI has no CDN dependency. The prompt editor provides supported-variable insertion, live preview, local draft status, clipboard actions, and database-backed version restore.

The content queue is the approval workspace. A UTF-8 CSV import accepts `Keyword` plus optional `Landing Page`, `Type`, `Title`, and `Word Count` columns, validates every row against the authenticated owner's active projects/content types, and creates draft tasks without invoking AI. Task titles are optional; a blank title is preserved as an explicit instruction for generation to create a distinct project-scoped title, while the keyword remains the temporary UI label. Users may edit the keyword, landing page, and type inline, then explicitly select up to 100 rows to proceed through the same durable queue reservation used by individual and scheduled generation. Completed rows link to their ownership-checked generated content page.

## Configuration and deployment

`config/settings.py` reads `.env` once, configures secure production cookie defaults, and registers a minute-based Beat schedule. `.env` and runtime files are ignored. `AI_CREDENTIAL_ENCRYPTION_KEY` is a Fernet master key held outside the database. Django admin is restricted to superusers for provider configuration; submitted API keys are encrypted before persistence and only masked hints are shown afterward. `AIProviderSelection` is a singleton relational pointer, so exactly zero or one database profile is active. Workers resolve it for every generation execution, allowing provider/model/key changes without restarts. If no database profile is active, `OPENAI_API_KEY` and `OPENAI_MODEL` remain the backward-compatible fallback.

Production deployments should use PostgreSQL, Redis, separate web/worker/Beat processes, HTTPS, exact host/origin settings, a production static server, and authenticated media routes. The current raw-TCP PostgreSQL/Redis architecture is intentionally local/server oriented and is not a Cloudflare Worker deployment.

## Test contract

The minimum verification commands are:

```bash
python manage.py check
python manage.py test
python manage.py makemigrations --check --dry-run
```

Coverage includes authentication, navigation, live readiness, owner isolation, upload validation/extraction, prompt restrictions, task/CSV/bulk creation, inline queue editing, selected-row authorization, encrypted provider switching and non-disclosure, configured/unconfigured provider paths, generation idempotency, due scheduling, stale recovery, version snapshots, private/escaped exports, and smoke rendering of every primary page. Provider calls are mocked.

## Known production-scale boundaries

The MVP does not claim organization/role-based multi-tenancy, external secret-manager integration or automated key rotation, malware scanning, semantic retrieval, cost quotas, factual verification, rich HTML editing, or complete provider-specific feature parity. These are future hardening or expansion areas, not nonfunctional buttons in the current interface.
