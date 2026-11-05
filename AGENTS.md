# Maintaining this collection

This repository is the user's curated skill source for CC Switch.

- New GitHub skill links mean: inspect the repository, locate the intended SKILL.md, check redistribution permission, add the source to sources.json, sync, validate, and update the README table.
- Keep each skill at skills/<name>/SKILL.md with its complete runtime resources and upstream license. Use actual files, not Git submodules.
- Preserve upstream content. Do not edit mirrored prompts or run upstream code while collecting them.
- sources.json is the source of truth. scripts/sync_skills.py owns skills/ and sources.lock.json, including removals from this mirror.
- Do not add a source without a verified license that permits redistribution. Flag license changes for review.
- Test with python3 -m unittest discover -s tests -v and python3 scripts/sync_skills.py --check.
- Keep scheduled automatic updates enabled. Never force-push.
- Report repository changes separately from updates to the user's installed local skills.
