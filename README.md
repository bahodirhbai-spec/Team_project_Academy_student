# Academy Student Progress Tracker

## Purpose

This repository provides a one-page web application for tracking academy
students and their learning progress: each student's current topic,
status and latest quiz score.

It exists as an academy team project to practise the full web flow —
an HTML/JavaScript page that calls a Python FastAPI backend, which
validates data with Pydantic and stores it in SQLite.

## ✨ Features

- Add students — form that saves a student; the API returns it with a
  generated ID.
- Student table — lists all students loaded from the backend on every
  page load.
- Update students — inline edit of topic, status and quiz score
  (`PATCH`).
- Status filter — shows only `Active`, `Paused` or `Completed` students.
- Summary — total students, active students and average quiz score
  (calculated in Python with NumPy).
- Validation — rejects blank names/topics, unknown statuses and scores
  outside 0–100; errors are shown on the page.
- Persistent storage — SQLite database file; data survives browser
  refresh and server restart.
- Central configuration — everything in `backend/config/`: settings
  (overridable via `.env`) and business rules, in separate files.
- Automated tests — pytest suite covering every endpoint and rule.

## Ownership

- Team: Academy student team
- Maintainers:
  - Hasan — updating students, filtering, summary (frontend + backend)
  - Bahodirjon — adding and listing students, form, database operations

## Project Status

Active development — academy training project, not used in production.

## Prerequisites

- [Python](https://www.python.org/downloads/) 3.12+ — application
  runtime (tested with 3.12.3). Includes SQLite through the built-in
  `sqlite3` module, so no separate database server is needed.
- [Git](https://git-scm.com/downloads) 2.0+ — to clone the repository.
- A modern web browser (Chrome, Firefox, Edge) — to use the page and its
  DevTools Network tab.

Python packages are installed from `requirements.txt` (pinned versions):
[FastAPI](https://fastapi.tiangolo.com/),
[Uvicorn](https://www.uvicorn.org/),
[Pydantic](https://docs.pydantic.dev/),
[pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/),
[NumPy](https://numpy.org/),
[pytest](https://docs.pytest.org/),
[HTTPX](https://www.python-httpx.org/) (used by the test client) and
[pycodestyle](https://pycodestyle.pycqa.org/) (PEP 8 checker).

No credentials or external services are required.

## Quick Start

```bash
git clone https://github.com/bahodirhbai-spec/Team_project_Academy_student.git
cd Team_project_Academy_student

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env

pytest
python -m backend
```

Verify: open <http://127.0.0.1:8000> in a browser, or run in a second
terminal:

```bash
curl http://127.0.0.1:8000/api/summary
# {"total_students":0,"active_students":0,"average_score":null}
```

Stop the server with `Ctrl+C`.

## Configuration

Copy `.env.example` to `.env` (already done in Quick Start):

```bash
cp .env.example .env
```

Every value is optional and documented with comments in
[`.env.example`](.env.example), which is the source of truth. All
variables use the `ACADEMY_` prefix. The defaults live in
[`backend/config/settings.py`](backend/config/settings.py).

Business rules (score range 0–100, allowed statuses, text length) are
**not** environment variables. Change them in
`backend/config/business_rules.py`, then delete `students.db` so the
table is recreated with the new database rules.

## Common Commands

Run from the project root with the virtual environment activated
(`source .venv/bin/activate`).

```bash
python -m backend                    # start the server (settings from .env)
ACADEMY_PORT=8001 python -m backend  # start on another port
pytest                               # run all tests
pytest -v                            # run tests, show each test name
pycodestyle backend tests            # check PEP 8 style
deactivate                           # leave the virtual environment
```

Interactive API docs (try every endpoint in the browser):
<http://127.0.0.1:8000/docs>

## Usage Examples

With the server running:

```bash
# Add a student (returns it with its generated id)
curl -X POST http://127.0.0.1:8000/api/students \
  -H "Content-Type: application/json" \
  -d '{"name":"Hasan","topic":"Python","status":"Active","score":80}'

# List all students, or only one status
curl http://127.0.0.1:8000/api/students
curl "http://127.0.0.1:8000/api/students?status=Active"

# Update only the fields you send
curl -X PATCH http://127.0.0.1:8000/api/students/1 \
  -H "Content-Type: application/json" \
  -d '{"status":"Completed","score":95}'

# Summary: counts and average score
curl http://127.0.0.1:8000/api/summary
```

Full data format, endpoints and error responses:
[docs/api.md](docs/api.md).

## Testing and Quality

Run these before opening a PR:

```bash
pytest                       # all tests must pass
pycodestyle backend tests    # no output means PEP 8 is respected
```

Tests use a temporary database, so they never touch your `students.db`.
Reviewers must also run the teammate's branch locally (Quick Start)
before approving a PR.

## Troubleshooting

### `ModuleNotFoundError: No module named 'fastapi'`

The virtual environment is not active. Run `source .venv/bin/activate`,
then `pip install -r requirements.txt`.

### `ModuleNotFoundError: No module named 'backend'`

The command was run from another folder. `cd` into the project root
(the folder that contains `backend/`) and run it again.

### `address already in use` on port 8000

Another program is using the port. Start on a different port instead of
stopping the other program:

```bash
ACADEMY_PORT=8001 python -m backend
```

Or set `ACADEMY_PORT=8001` in `.env`.

### Page shows an error or the table stays empty

Open DevTools (F12) → **Network**, reload the page and click the
`students` request. Check its status code and response; the server
terminal also prints each request.

### A changed business rule is not applied

SQLite keeps the old `CHECK` rules inside the existing `students.db`.
Back up the file if you need its data, then delete it and restart the
server; a new table is created with the new rules. **This deletes all
saved students.**

## Related Docs / References

Project docs:

- [docs/api.md](docs/api.md) — data format, endpoints, error responses.
- [docs/architecture.md](docs/architecture.md) — folder structure,
  layers, request flow from page to database.
- [docs/demo.md](docs/demo.md) — demo checklist and Network tab
  walkthrough.

External references:

- [FastAPI documentation](https://fastapi.tiangolo.com/) — API
  framework.
- [Pydantic documentation](https://docs.pydantic.dev/) — data models
  and validation.
- [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
  — reading `.env` and environment variables.
- [Python `sqlite3` module](https://docs.python.org/3/library/sqlite3.html)
  — database access.
- [NumPy `mean`](https://numpy.org/doc/stable/reference/generated/numpy.mean.html)
  — average score calculation.
- [PEP 8](https://peps.python.org/pep-0008/) — Python style guide
  followed in this repository.
- [MDN Fetch API](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API)
  — how the page calls the backend.

## Support / Contact

- [Open a repository issue](https://github.com/bahodirhbai-spec/Team_project_Academy_student/issues)
  for bugs, questions or documentation problems.
