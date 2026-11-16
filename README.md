# Akademiya o'quvchilari — Academy Student Tracker

A one-page website to track academy students and their learning progress.
Built with HTML, CSS, JavaScript, Python FastAPI, Pydantic, NumPy and SQLite.

## Run it

```bash
# 1. Create a virtual environment (a private folder for this project's
#    Python packages) and install the packages. Only needed once.
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. Start the server (from the project root folder).
#    Host, port and reload come from backend/config.py / .env.
.venv/bin/python -m backend

# 3. Open the website:  http://127.0.0.1:8000
#    Interactive API docs: http://127.0.0.1:8000/docs
```

Run the tests:

```bash
.venv/bin/python -m pytest
```

The data is saved in `students.db` (SQLite). It stays after refreshing the
browser or restarting the server. Delete that file to start empty.

## Configuration

Settings live in `backend/config.py` (read with pydantic-settings).
Override them without changing code, with an environment variable or a
`.env` file (copy `.env.example` to `.env`):

```bash
ACADEMY_PORT=9000 ACADEMY_DATABASE_PATH=/tmp/demo.db .venv/bin/python -m backend
```

| Setting                    | Default            | Meaning                         |
|----------------------------|--------------------|---------------------------------|
| `ACADEMY_APP_TITLE`        | `Academy Students` | Name shown in the API docs      |
| `ACADEMY_HOST`             | `127.0.0.1`        | Address the server listens on   |
| `ACADEMY_PORT`             | `8000`             | Port the server listens on      |
| `ACADEMY_RELOAD`           | `true`             | Restart when code changes       |
| `ACADEMY_DATABASE_PATH`    | `students.db`      | SQLite file                     |
| `ACADEMY_AVERAGE_DECIMALS` | `2`                | Decimals in the average score   |

Business rules (score 0–100, text length, allowed statuses) are also in
`backend/config.py`, in the "Business rules" section. Change them by
editing that file (not `.env`). The validation and the database `CHECK`
rules are built from them. After changing a rule, delete `students.db`,
because an existing table keeps its old `CHECK` rules.

## Project structure

```
backend/
  config.py      ALL configuration: settings + business rules
  models.py      Pydantic models: data format and validation rules
  database.py    SQLite connection and table creation
  repository.py  All SQL queries for students
  services.py    Business logic: summary, average with NumPy
  routes.py      The 4 API endpoints
  main.py        Builds the app and serves the frontend
frontend/
  index.html     The page
  index.css      The styles
  app.js         Calls the API and updates the page
tests/
  test_api.py    Automated tests for every endpoint and rule
```

## Data format (agreed by both teammates)

Student:

```json
{ "id": 1, "name": "Hasan", "topic": "Python", "status": "Active", "score": 80 }
```

- `name`, `topic`: required, cannot be blank
- `status`: `Active`, `Paused` or `Completed`
- `score`: whole number 0–100, or `null` (no score yet)

Summary:

```json
{ "total_students": 3, "active_students": 2, "average_score": 76.67 }
```

`average_score` is `null` when nobody has a score ("No scores yet.").

## Endpoints

| Method | Path                     | Purpose                                   | Owner      |
|--------|--------------------------|-------------------------------------------|------------|
| POST   | `/api/students`          | Add a student (returns it with its ID)    | Bahodirjon |
| GET    | `/api/students`          | List students; `?status=Active` filters   | Bahodirjon / Hasan |
| PATCH  | `/api/students/{id}`     | Update topic, status and/or score         | Hasan      |
| GET    | `/api/summary`           | Counts and NumPy average score            | Hasan      |

Invalid data gets **422** with an explanation; an unknown ID gets **404**.
The webpage shows these errors in red.

## Request flow (add a student)

1. The user fills in the form and clicks **Save**.
2. `app.js` sends `POST /api/students` with the student as JSON.
3. FastAPI validates it with the `StudentCreate` Pydantic model.
4. `StudentRepository.add` runs `INSERT` in SQLite and gets the new ID.
5. The API returns the saved student including `id` (status 201).
6. `app.js` shows a success message and reloads the table and summary.
7. On every page load, `app.js` calls `GET /api/students` again.

## Demo checklist

1. Add three students, for example with scores 80, 70 and 90.
2. Edit one of them (the "Tahrirlash" button) and save.
3. Use the status filter.
4. Check the average: (80 + 70 + 90) / 3 = 80.
5. Stop the server (Ctrl+C), start it again, reload the page:
   the students are still there.
6. Open DevTools (F12) → **Network** tab, click Save, then click the
   `students` request to show the Payload (sent) and Response (received).
