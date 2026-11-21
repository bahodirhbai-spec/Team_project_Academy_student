# Branches and review notes

The work is split so each feature can be reviewed on its own. The
contract was written first in `docs/data-contract.md`; both feature
branches were built from it.

| Branch | Contents | Merged into integration as |
|---|---|---|
| `feature/profile-contract` | agreed tables, status values, JSON models, pandas dependency | base |
| `feature/bahodirjon-topics` | catalogue, learning records, pandas topic processing, NumPy matrix | `Merge PR: Bahodirjon ...` |
| `feature/hasan-projects` | projects, topic links, pandas project summaries, NumPy applied counts | `Merge PR: Hasan ...` |
| `feature/profile-integration` | generated labels, profile page, cross-review tests, docs | kept intact on the final feature branch |
| `feature/student-profile-dashboard` | all of the above plus the no-direct-push rule | pushed for review; **do not push to `dev` or `main`** |
| `feature/remove-skill-summary-section` | removes the global skill/project summaries, their API endpoints and the NumPy matrix | pushed for review |

The global summary endpoints and the NumPy matrix were removed later: the
page no longer displays them, and the profile feature does not depend on
them. Historical rows above describe what each feature branch originally
contained.

The profile work was accidentally pushed to `dev` once. It was moved to
`feature/student-profile-dashboard` and `dev` was restored to its previous
commit (`21be005`). See `AGENTS.md`: never push directly to `dev`, `main`
or `Academy_student`; use a feature branch and a reviewed PR instead.

Commits use a neutral team identity because this workspace has a single
Git identity. The branch names and the ownership table record who each
part belongs to. The merge commits below are PR-style integration points
kept on the feature branch, not on `dev`.

## Review evidence

Each local merge was tested before it was made:

- `feature/bahodirjon-topics`: 43 tests passed, including duplicate
  topics, unknown IDs, status changes, duplicate-skill handling and
  restart persistence.
- `feature/hasan-projects`: 42 tests passed, including a project link
  from another student, invalid links, status changes and persistence.
- `feature/profile-integration`: all tests passed after merging; the
  `main.py` router registration conflict was resolved by registering all
  three routers.

Cross-review tests in `tests/test_profile.py`:

- `test_hasans_review_topic_status_changes_update_profile` —
  Hasan's review of Bahodirjon's topic feature: changing a learning
  record must update the generated skill in both directions.
- `test_bahodirjons_review_project_status_changes_update_skill_label` —
  Bahodirjon's review of Hasan's project feature: changing a project
  status must switch the label between `Learned` and
  `Applied in a project`.

Both were run against the merged branch, not only against their own
feature branch.

## Reviewer checklist for the real PRs

1. `pip install -r requirements.txt`
2. `pytest`
3. `pycodestyle backend tests`
4. `node --check frontend/app.js` (if Node is installed)
5. Follow the profile walkthrough in [demo.md](demo.md).
6. Confirm the error cases listed in
   [data-contract.md](data-contract.md#error-cases-agreed-for-tests).
