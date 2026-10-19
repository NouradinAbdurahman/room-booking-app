# 14: README and AI_NOTES

**What to build:** A reviewer can run the app and the tests from the README alone, understand every main design decision, and see honestly how AI was used (brief "How to submit" and "Using AI"; spec §8; acceptance criteria 25–28).

**Blocked by:** 09, 12, 13

**Status:** done

- [ ] **README sections:**
  - Quick start: copy `.env.example`, then `docker compose up --build`, then open `http://localhost:5173`.
  - Demo logins, with the password clearly marked as a local demo value.
  - Backend and frontend test commands.
  - The endpoint table and the error format.
  - Design decisions, a few lines each, linking the ADRs.
  - Indexes and why.
  - How performance was checked, from ticket 13.
  - The constraint evidence (`\d` and `sqlmigrate`), from ticket 06.
  - Which tests were written and why.
  - The CSRF-through-proxy check, from ticket 04.
  - The three brief/ADR differences flagged in the spec, and the assumptions it lists.
  - That `DEBUG=False` requires HTTPS (ADR 0004), and why HSTS preload and the proxy SSL header are off.
  - What I'd improve with more time, including a per-User rate limit on creating Bookings (deliberately out of scope; see `evidence/12-security-checklist.md` for the security review's reason).
- [ ] **`AI_NOTES.md`:**
  - the tools used and for which parts;
  - at least two real places where AI was wrong or weak and what was done about each. Candidates from the design phase: the unproven "max 96 per Day" claim; the extra "no cancelling after start" rule; the inconsistent response and error shapes in the API visual. Add any found during implementation.
- [ ] **The independent decision is left as a clearly marked placeholder for the author.** Neither the implementer nor the AI chooses, invents or drafts it. The ticket cannot close until the author has supplied it.
- [ ] **Fresh-clone check:** following only the README on a clean checkout, the app starts, the demo logins work, and both test suites pass.
- [ ] `git log` shows small, incremental commits throughout. There is no single big final commit.
