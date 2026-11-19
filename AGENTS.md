# Agent Instructions

## Git workflow (mandatory)

- **Never push directly to `dev`, `main`, or `Academy_student`.**
- Branch from the current integration branch with a short name:
  `feature/<short-description>` or `fix/<short-description>`.
- Commit, test, and push **only that feature branch**.
- Open a pull request for review. Do not merge or push to `dev`/`main`
  yourself unless a human explicitly asks for a one-time corrective
  history fix.
- Ask before any force-push or history rewrite. Use
  `git push --force-with-lease` when a corrective rewrite is requested.

### History note

On 2026-11-19 the profile work was accidentally pushed to `dev`. It was
moved to `feature/student-profile-dashboard` and `dev` was restored to
`21be005`. Do not repeat that mistake.

## Verification before pushing a feature branch

From the project root, with the virtual environment active:

```bash
pytest
pycodestyle backend tests
node --check frontend/app.js   # if Node is installed
```

Keep existing student features working. The agreed database and API
contract lives in `docs/data-contract.md`; branch/review notes live in
`docs/pull-requests.md`.
