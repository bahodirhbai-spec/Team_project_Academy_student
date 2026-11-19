# Branches and review notes

The work is split so each feature can be reviewed on its own. The
contract was written first in `docs/data-contract.md`; both feature
branches were built from it.

| Branch | Contents | Merged into integration as |
|---|---|---|
| `feature/profile-contract` | agreed tables, status values, JSON models, pandas dependency | base |
| `feature/bahodirjon-topics` | catalogue, learning records, pandas topic processing, NumPy matrix | `Merge PR: Bahodirjon ...` |
| `feature/hasan-projects` | projects, topic links, pandas project summaries, NumPy applied counts | `Merge PR: Hasan ...` |
| `feature/profile-integration` | generated labels, profile page, cross-review tests, docs | merged into `dev` as `Merge PR: student profile feature into dev` |

Commits use a neutral team identity because this workspace has a single
Git identity. The branch names and the ownership table record who each
part belongs to. These are local, PR-style merge commits; no GitHub PR
was opened because this environment is not authenticated to GitHub. Push
the branches and open/approve the real PRs when both teammates are
available, using the notes below as the PR descriptions.

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

- `test_hasans_review_topic_status_changes_update_matrix_and_profile` —
  Hasan's review of Bahodirjon's topic feature: changing a learning
  record must update both the matrix and the generated skill.
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
