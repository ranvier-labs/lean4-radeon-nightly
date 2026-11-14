# Distribution repository

Do not publish compiler sources, source Git history, private logs, credentials,
or unreviewed files here. Keep archives out of Git. Public headers and compiled
modules belong in release assets. Never replace a published release record,
tag, or asset; publish a new `-revN` instead.

Run `make check`, `make build`, and `git diff --check` before publishing changes.
Use Lean-style commit subjects: `feat: add ...`, `fix: ...`, or `doc: ...`.
Keep compiler builds and GPU runners in the separate source repository. Do not
claim GPU execution when tests skip or no GPU is available.
