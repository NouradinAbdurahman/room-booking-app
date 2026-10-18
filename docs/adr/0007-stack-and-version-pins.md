# Stack and exact version pins

The stack is Django REST Framework on PostgreSQL, a React + Vite frontend, and Docker Compose to run it all. The brief fixes Django, PostgreSQL and React; DRF, Vite and Compose are the conventional choices around them.

Versions are pinned exactly, so the reviewer runs what we tested:

| Component | Pin | Why |
| --------- | --- | --- |
| PostgreSQL | `postgres:17` image | Current major version; supports `btree_gist` and exclusion constraints |
| Python | 3.13 | Supported by both Django 5.2 and DRF 3.18 |
| Django | `5.2.18` | 5.2 LTS (latest patch at the time of pinning) |
| djangorestframework | `3.18.3` | See the compatibility check below |

DRF compatibility was **checked, not assumed** (2026-10-19). DRF 3.18.3 on PyPI declares `requires_dist: django>=5.2` and the classifier `Framework :: Django :: 5.2`, and its own `tox.ini` at tag `3.18.3` runs the test suite against `django52` on Python 3.10–3.14.

## Consequences

- PostgreSQL 17 is the version the migration and exclusion-constraint checks in ADR 0001 run against.
- Frontend package versions are locked by the committed `package-lock.json`.
