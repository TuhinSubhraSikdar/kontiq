# Kontiq Development Instructions

This file is the permanent instruction set for human and AI contributors working in this repository. Its scope is the entire repository. More specific `AGENTS.md` files may add local constraints but may not weaken these rules.

## Required workflow

1. Always inspect existing code before changing it.
2. Before implementing a feature, inspect the relevant models, migrations, forms, views, URLs, services, tasks, templates, static assets, and tests.
3. Read `README.md` and `PROJECT_STRUCTURE.md` before making architectural changes.
4. Preserve existing working functionality. Never destroy, replace, or silently remove behavior to simplify a change.
5. Keep the implementation within the current roadmap phase unless the user explicitly expands scope.
6. Make the smallest coherent change that completes the requested behavior; do not leave fake buttons, placeholder actions, or nonfunctional forms.
7. After a change, run the relevant tests, `python manage.py check`, and migration consistency checks when models may be affected.
8. Report what changed, files created or modified, tests performed, and anything incomplete.

## Architecture and code organization

- Follow the architecture and app ownership defined in `PROJECT_STRUCTURE.md`.
- Keep Django apps modular and organized by domain responsibility.
- Keep views thin. Views handle HTTP concerns and delegate workflows to reusable services.
- Put browser input validation in Django forms and domain invariants in models/services as appropriate.
- Use reusable services for business workflows shared by views, admin actions, management commands, and Celery tasks.
- Keep AI integrations separate from Django views and models. SDK calls belong in provider adapters under `apps/ai_engine`.
- Celery tasks must be thin, idempotent entry points into services. Do not duplicate generation logic in task functions.
- Use Django ORM rather than raw SQL unless raw SQL is genuinely necessary and documented with portable fallback considerations.
- Avoid cross-app circular imports. Depend on stable service contracts, settings, and model references by string where appropriate.
- Prefer explicit types, meaningful names, small functions, and clear error boundaries over clever abstractions.
- Avoid unnecessary dependencies. Explain and document each material addition.

## Data and migrations

- Create migrations whenever model definitions change; never edit an applied migration casually.
- Use foreign keys, related names, indexes, constraints, and transactions deliberately.
- Retain PostgreSQL compatibility even while SQLite is the local default.
- Treat the relational database as the source of truth for task state. Redis is transport and coordination infrastructure, not durable business storage.
- Protect generation against duplicate execution with durable state/lock tokens and transactional transitions. Do not rely only on Celery delivery semantics.
- Never hardcode dashboard statistics. Derive counts and totals from database records through query/service code.
- Do not silently delete records or generated artifacts. Make deletion behavior explicit and test it.

## Security and privacy

- Use environment variables for secrets. Never commit `.env` files, credentials, tokens, or real API keys.
- Never expose API keys in frontend HTML, form initial values, logs, tracebacks, activity records, or user-facing error messages.
- If credentials are stored in the database later, encrypt them with a master key held outside the database and show only masked identifiers.
- Follow Django security best practices: authentication, authorization, CSRF protection, safe redirects, secure cookies in production, host validation, and escaped templates.
- Scope every project-owned query to the authenticated user/tenant boundary once ownership is introduced. Object IDs alone are never authorization.
- Validate and normalize all user input. Reject unexpected upload types, misleading extensions, excessive sizes, unsafe filenames, and invalid URLs.
- Serve private media through authorized download views; do not assume an obscure media URL is access control.
- Treat uploaded/reference text and generated AI output as untrusted. Avoid executing it and sanitize HTML at trust boundaries.
- Use proper exception handling. Log actionable context without secrets or unnecessary customer content, and present safe errors to users.

## AI generation rules

- Provider adapters implement a common interface and return provider-neutral results.
- Prompt assembly, provider invocation, parsing, validation, correction attempts, document rendering, and persistence are separate stages.
- Prompt templates are user-controlled data. Validate supported variables and report unknown variables clearly.
- Keep global instructions, project context, content-type prompts, project overrides, and task data distinguishable during assembly.
- Never claim generated content is factually verified merely because structural validation passes.
- Enforce configurable output, timeout, and retry limits. Retries must be bounded and observable.
- Do not log assembled prompts or raw provider responses by default because they may contain sensitive business data.
- Preserve provider response identifiers and safe usage metadata where useful for auditability.

## Background processing

- Never perform lengthy AI generation synchronously in a normal HTTP request.
- Queue manual and scheduled generation through the same idempotent workflow.
- Make task status transitions explicit and test valid/invalid transitions.
- Acknowledge that Celery delivery is at least once: locks, idempotency, and duplicate prevention belong in application logic.
- Use the database as the authority for scheduled work. Celery Beat may trigger a due-work dispatcher; do not depend on long-lived ETA messages for durable scheduling.
- Record failures and retries without storing API keys or unsafe provider payloads.

## Templates and user experience

- Keep templates reusable with a shared base and focused components/partials.
- Use semantic HTML, accessible labels, keyboard-usable controls, clear focus states, and responsive behavior.
- Every visible action must work, be disabled with an honest explanation, or be omitted until implemented.
- Use status badges and notifications consistently; never obscure failed processing.
- Keep the interface professional and restrained: dark navigation, light workspace, subtle borders, consistent spacing, and no unnecessary animation.
- Verify actual rendered pages for significant UI changes; template syntax passing is not visual verification.

## Testing and quality

- Write tests for important functionality, especially authorization, form validation, service workflows, status transitions, retry/idempotency behavior, file validation, prompt assembly, and downloads.
- Prefer fast unit tests for pure services and focused Django integration tests for database/HTTP behavior.
- Mock provider/network calls; automated tests must not consume paid AI APIs.
- Test failure paths as well as success paths.
- Run relevant tests after modifications. The minimum checks for broad changes are:

```bash
python manage.py check
python manage.py test
python manage.py makemigrations --check --dry-run
```

## Documentation and change reporting

- Update `README.md` whenever setup, dependencies, commands, environment variables, services, or important architecture decisions change.
- Update `PROJECT_STRUCTURE.md` whenever the actual tree, app responsibilities, data relationships, storage paths, or service boundaries change.
- Keep implemented and planned behavior clearly distinguished. Documentation must match the repository; do not describe planned features as working.
- Document important technical decisions and their tradeoffs in `PROJECT_STRUCTURE.md` or a future architecture decision record.
- Do not silently skip incomplete requirements. Call out deferred or blocked behavior explicitly.

Every completion report must include:

- What changed.
- Which files were created or modified.
- Which tests and checks were run, including results.
- What remains incomplete or intentionally deferred.
