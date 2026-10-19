# AI notes

## Tools, and what each was used for

| Tool | Used for |
| --- | --- |
| **ChatGPT** | Planning and structuring the project: discussing the requirements, architecture, technical decisions and workflow; reviewing Claude's reports between tickets; preparing my instructions for the next step |
| **Claude Code**, with the **Claude Opus 5.5** model | The main coding agent: architecture decision records, the spec and tickets, implementation, tests, code reviews, browser checks (Playwright), and this documentation |
| **[Matt Pocock's skills](https://github.com/mattpocock/skills)** inside Claude Code | Structured workflows the agent followed: `setup`, `grill-with-docs` (design questions and ADRs), `to-spec`, `to-tickets`, `implement`, `tdd` and `code-review` |

## How I worked with AI

I used ChatGPT for planning and structuring the project, and Claude Code with Claude Opus 5.5 as the primary coding agent. I wanted AI's speed and its ability to reason about complex tasks, while staying actively involved in directing and checking the work.

This project reinforced one lesson: an AI agent can do a great deal of software engineering, but the quality of the result depends on three things:
- how clearly the requirements are defined;
- how the work is organised;
- how carefully the output is verified.

AI can misunderstand requirements, make unsupported claims, introduce bugs, or add behaviour nobody asked for. So I treated the agent's work as something to inspect and test, not to accept automatically.

**Why I used Matt Pocock's skills.** They made the agent follow a disciplined, traceable process instead of generating code from broad prompts:
1. Define the requirements.
2. Record the architecture decisions (`docs/adr/`).
3. Break the work into 14 reviewable tickets (`.scratch/room-booking-app/issues/`).
4. Implement each one test-first.
5. Review it, using two independent reviewers: one against the project's standards, one against the spec.
6. Commit in small steps.

I approved each ticket before the next one started.

The skills do not guarantee correct output. I still reviewed the agent's reasoning, challenged its assumptions, checked the tests and the database behaviour, and decided whether each proposed change matched the assignment. The final responsibility for the requirements and the technical decisions is mine.

## Where the AI was wrong or weak, and what was done

Each item happened in this project and is visible in the Git history or the evidence files.

1. **An unproven claim presented as fact.**
   - What happened: while designing pagination, Claude stated that a Room "can hold at most 96 bookings in a day", then used that to argue one page of 100 would always hold a whole Day.
   - What I did: I rejected the claim and required the behaviour to be verified rather than assumed.
   - Result: the frontend follows every page, and tests check pagination with bookings that cross midnight.

2. **A rule the brief didn't ask for.**
   - What happened: Claude proposed that bookings cannot be cancelled once they have started.
   - What I did: I rejected it. The brief's only rule is that the creator cancels.
   - Result: a Booker may cancel any of their bookings at any time (ADR 0002), and the README states this reading of the brief.

3. **An inflated performance claim.**
   - What happened: Claude reported that its query change made the Day schedule go from 9.7 ms to 0.057 ms, and put that in a commit message.
   - Why it was wrong: its own seed command had refreshed planner statistics only for the bookings table. PostgreSQL believed there were 3 Rooms and chose a bad plan, so the "before" figure was an artifact.
   - How it was caught: a spec review asked for every number to be backed by a saved plan, and re-measuring showed the discrepancy.
   - Result: the fair gain is 2–20×, measured three times with fresh statistics. The evidence file states the correction. The lasting win, the index now reading only matching rows, holds either way.

4. **A security setting that broke the app.**
   - What happened: after a deploy check, Claude added an HTTPS redirect that redirected every request to an HTTPS port nobody served when `DEBUG` was off.
   - What was done: a review caught it and it was removed. A later security review argued for the redirect again.
   - Result: after weighing both, it was restored and **documented**: `DEBUG=False` requires HTTPS (ADR 0004).
   - Lesson: two automated reviewers disagreed, and the right answer needed a human decision about what "production-safe" means here.

5. **A destructive command outside the project.**
   - What happened: while cleaning up a test container, Claude ran `docker volume prune -f`, which affects every Docker project on the machine.
   - Effect: named volumes survived, but any unused anonymous volume elsewhere could have been deleted. Claude reported it immediately.
   - Result: I then explicitly forbade global Docker cleanup for the rest of the project.

6. **False "all clear" results from a broken check.**
   - What happened: during the security sweep, a shell quoting error made three searches (for CORS, raw SQL and logging) fail. The script printed "none found" anyway.
   - What was done: Claude noticed, re-ran the searches correctly, and confirmed they do find matches in test files before recording the results.

7. **Running an attack payload against the wrong code.**
   - What happened: after an edit script stopped halfway, Claude ran an injection test (a fake index name that also tried to drop a table) against the *old, vulnerable* development command, on the development database.
   - Effect: it failed harmlessly, inside a rolled-back transaction.
   - What was done: Claude checked every table and index was intact, then fixed the command to accept only real index names, quoted safely.

8. **Bugs the tests or reviews found in AI-written code:**
   - Two truly simultaneous bookings could **deadlock** in PostgreSQL. The data stayed correct, but the loser got a `500`; the race test exposed it, and the insert is now retried.
   - A failed logout looked successful while the server session stayed alive.
   - A time with an offset like `+03:00:30` slipped past the whole-minute rule.
   - The browser's date formatting printed "Sept", where the design uses "Sep".
   - Some tests could never fail, for example an `updated_at` check.

   Each was fixed with a test that failed first.

## A decision I made myself

> **[PLACEHOLDER: for Nouraddin to write.]** Record one genuine decision you made against, or without, the AI's suggestion: the alternatives you considered, and why you chose as you did. This section is intentionally left for you; it must not be chosen or written by an AI.
