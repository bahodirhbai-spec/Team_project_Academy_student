# Demo Checklist

Start from an empty database to make the demo predictable:
stop the server, delete `students.db` (only if its data is not needed),
then run `python -m backend` and open <http://127.0.0.1:8000>.

## 1. Empty state

The table is empty and the summary shows "No scores yet."

## 2. Add three students

| Name       | Topic   | Status    | Score |
|------------|---------|-----------|-------|
| Hasan      | Python  | Active    | 80    |
| Bahodirjon | FastAPI | Active    | 70    |
| Ali        | SQL     | Paused    | 90    |

Summary: 3 students, 2 active, average **80**
(`(80 + 70 + 90) / 3 = 80`).

## 3. Show validation

Type only spaces as the name and click **Save**: a red error from the
API appears (the browser lets spaces through, Python rejects them).

## 4. Update one student

Click **Tahrirlash** on Ali, change the status to `Completed` and the
score to `60`, click **Saqlash**.
New average: `(80 + 70 + 60) / 3 = 70`.

## 5. Filter by status

Choose `Active` in the filter: only Hasan and Bahodirjon are shown.

## 6. Show that data persists

1. Refresh the browser: the students are still there.
2. Stop the server (`Ctrl+C`), start it again (`python -m backend`),
   refresh: the students are still there, because they are stored in
   `students.db`.

## 7. Show a profile and generated skills

1. Click **View Profile** on Hasan.
2. Add `Git branches and pull requests` with status `Completed`. The
   profile shows **Git collaboration — Learned**.
3. Add a project linked to that topic, with your own contribution and a
   repository link, and set it to `Completed`. The label becomes
   **Applied in a project** and shows the link and contribution.
4. Change the project back to `In progress`: the label returns to
   **Learned**. Change the topic to `Learning`: the skill disappears.
5. Add both Python topics from the catalogue. They merge into one
   **Python basics** skill with two supporting topics.
6. Click **Orqaga**. The page returns to the student table and the simple
   count/average summary.

## 8. Network tab: one request from page to database

1. Press **F12** → **Network** tab, select **Fetch/XHR**.
2. Add a student and click **Save**.
3. Click the `students` request:
   - **Headers**: `POST /api/students`, status `201 Created`.
   - **Payload**: the JSON that JavaScript sent.
   - **Response**: the saved student, now with its `id`.
4. Explain the path, using [architecture.md](architecture.md)
   ("Request flow"): `app.js` → FastAPI route → Pydantic validation →
   repository `INSERT` → SQLite → response → table refresh.

Each teammate explains one request (for example Bahodirjon `POST`,
Hasan `PATCH` or `GET /api/summary`).
