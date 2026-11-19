## Summary
- GET /api/students?search= : partial, case-insensitive search by student name
  (surrounding spaces ignored, blank search = no filter); combines with ?status=;
  no match returns [].
- GET /api/students?sort=name_asc|name_desc : sort by name A-Z / Z-A, ignoring case.
  Any other value returns 422 listing the allowed values.
- Without the new parameters the list keeps its ID order.
- GET /api/students/{id} : one student, or 404 "Student {id} not found".
- Frontend: search box next to the list heading (restores PR #2, which was
  reverted until backend search existed). The browser-side filter also matches
  the name only, so it agrees with the API.

## How the SQL stays safe
- The search text and status are passed as named parameters (:search, :status),
  never pasted into the SQL string.
- ORDER BY comes from a fixed dictionary keyed by the StudentSort enum.
- instr() is used instead of LIKE, so % and _ are matched as normal characters.

## How to test
1. pip install -r requirements.txt
2. python -m pytest -q          (all tests pass)
3. pycodestyle backend tests    (no output)
4. python -m backend, open http://127.0.0.1:8000/docs and try:
   search=ali, search=ali&status=Active, sort=name_asc, sort=name_desc,
   sort=bad (422), GET /api/students/1, GET /api/students/9999 (404)

## Tests added
Partial and case-insensitive search, surrounding spaces, search + status,
search does not match topic, both sort directions, search + sort,
no matching students, invalid sort (422), % is not a wildcard,
existing and nonexistent student IDs, default behaviour unchanged.
