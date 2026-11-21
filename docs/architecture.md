# Architecture

## Overview

```
┌────────────┐   HTTP + JSON   ┌──────────────┐    SQL    ┌──────────┐
│  Browser   │ ──────────────► │   FastAPI    │ ────────► │  SQLite  │
│ HTML/CSS/JS│ ◄────────────── │   (Python)   │ ◄──────── │ (a file) │
└────────────┘                 └──────────────┘           └──────────┘
   frontend/                       backend/                students.db
```

The database is the source of truth: after every change the page asks
the API again instead of trusting what is on the screen.

## Folder structure

```
backend/
  config/        All configurable values, in two files:
    settings.py        where the app runs: .env, port, paths
    business_rules.py  score range, text length, statuses
  models.py           Pydantic models: data format and validation
  database.py         SQLite connections and all CREATE TABLE statements
  repository.py       All SQL queries for students
  topic_repository.py All SQL for learning records (Bahodirjon)
  project_repository.py All SQL for projects and links (Hasan)
  topic_analytics.py  pandas topic frames + NumPy skill matrix
  project_analytics.py pandas project frames + NumPy applied counts
  skill_analytics.py  pandas join producing generated skills
  services.py         Business logic: summary, NumPy average
  topic_service.py    Catalogue, learning records, matrix summary
  project_service.py  Projects, links, project summary
  profile_service.py  Integration: profile + combined summary
  routes.py           Existing student endpoints
  topic_routes.py     Topic and catalogue endpoints
  project_routes.py   Project endpoints
  profile_routes.py   View Profile endpoint
  main.py             Builds the FastAPI app, serves the frontend
  __main__.py         "python -m backend": starts uvicorn from settings
frontend/
  index.html          The page + profile view
  index.css           The styles
  app.js              Calls the API and updates the page
tests/
  test_api.py         Existing student endpoint tests
  test_topics.py      Topic and matrix tests (Bahodirjon)
  test_projects.py    Project and link tests (Hasan)
  test_profile.py     Cross-feature profile and review tests
  test_frontend.py    Static asset wiring checks
docs/                 Detailed documentation (this folder)
```

## Layers (Clean Architecture)

Each file has one responsibility, and dependencies point inward:

| Layer (inner → outer) | File(s)                          | Knows about              |
|-----------------------|----------------------------------|--------------------------|
| Business rules        | `config/business_rules.py`       | nothing in the project   |
| Domain models         | `models.py`                      | business rules           |
| Business logic        | `services.py`, `topic_service.py`, `project_service.py`, `profile_service.py`, `*_analytics.py` | models, business rules, pandas, NumPy |
| Data access           | `database.py`, `repository.py`, `topic_repository.py`, `project_repository.py` | models, business rules |
| Web (HTTP)            | `routes.py`, `topic_routes.py`, `project_routes.py`, `profile_routes.py` | everything above, settings |
| Startup ("Main")      | `main.py`, `__main__.py`, `config/settings.py` | everything |

The two config files sit at opposite ends on purpose. The business
rules are the innermost layer, so they import nothing. The settings
read `.env` and the environment, which makes them part of the
outermost layer, the startup code (Clean Architecture calls it
"Main"). Keeping them in separate files means `models.py` can import
the rules without loading `.env`. `config/__init__.py` is kept empty
for the same reason.

All SQL stays in `database.py` and `repository.py` (Clean
Architecture: "all SQL should be restricted to this layer").

Consequences:

- Changing the database only changes `database.py` and `repository.py`.
- `services.py` has no web or SQL code, so it is easy to test.
- Routes receive the repository and settings through FastAPI
  `Depends(...)` (dependency injection), so tests can run the app with a
  temporary database via `create_app(Settings(database_path=...))`.

## Request flow: adding a student

1. The user fills in the form and clicks **Save**.
2. `app.js` (`handleFormSubmit`) sends `POST /api/students` with the
   student as JSON.
3. FastAPI validates the body with the `StudentCreate` Pydantic model.
   Invalid data stops here with a 422 response.
4. `StudentRepository.add` runs `INSERT` in SQLite; SQLite generates
   the `id`.
5. The API returns the saved student including `id` (status 201).
6. `app.js` shows a success message and reloads the table and summary.
7. On every page load, `app.js` calls `GET /api/students` and
   `GET /api/summary` again, so the page always shows what is saved.

## Request flow: View Profile

1. The table's **View Profile** button sets `#profile/3` in the URL.
2. `app.js` calls `GET /api/students/3/profile`.
3. `ProfileService` loads the student, their learning records and their
   projects through the repositories.
4. `skill_analytics.py` merges completed topics with completed project
   evidence in pandas and calculates each skill label. Nothing about the
   label is written to SQLite.
5. `topic_analytics.py` builds the NumPy matrix for the global summary;
   `project_analytics.py` combines project rows with it for the counts.
6. The page renders cards with text nodes and validated links, so a
   student-entered repository URL cannot inject HTML.

## Configuration vs business rules

The `config/` folder has two files:

- **Settings** (`config/settings.py`, pydantic-settings): host, port,
  database path and similar. They depend on the computer, so they can be
  overridden in `.env` or with `ACADEMY_*` environment variables.
- **Business rules** (`config/business_rules.py`): score range, text
  length, allowed statuses. They are edited only in that file. Both
  the Pydantic validation and the SQLite `CHECK` constraints are built
  from them, so each rule is written once.

The frontend (`index.html`, `app.js`) still repeats the statuses and
0–100 for the form, because browser JavaScript cannot read Python files.
The backend validates everything regardless.
