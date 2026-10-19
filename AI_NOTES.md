# AI notes

## Tools, and what each was used for

| Tool | Used for |
| --- | --- |
| **ChatGPT** | Planning and structuring the project: requirements, architecture, technical decisions and workflow; reviewing Claude's reports between tickets; preparing my instructions for each next step |
| **Claude Code**, with the **Claude Opus 5.5** model | The main coding agent: architecture decision records, spec and tickets, implementation, tests, code reviews, browser checks (Playwright), and this documentation |
| **[Matt Pocock's skills](https://github.com/mattpocock/skills)** inside Claude Code | Structured workflows the agent followed: `setup`, `grill-with-docs`, `to-spec`, `to-tickets`, `implement`, `tdd` and `code-review` |

## How I worked with AI

I treated the agent's work as something to inspect and test, not to accept automatically. AI can misunderstand requirements, make unsupported claims, introduce bugs, or add behaviour nobody asked for.

The workflow:
- requirements and architecture decisions written down first (`docs/adr/`);
- 14 reviewable tickets;
- test-first implementation;
- two independent reviews per ticket, one against the project's standards and one against the spec;
- small commits.

I approved each ticket before the next one started. The workflow does not guarantee correct output; I still checked the reasoning, the tests and the database behaviour. The final responsibility for the requirements and the technical decisions is mine.

## Where the AI was wrong or weak, and what was done

These all happened in this project. Most are recorded in the Git history, the spec or the evidence files.

1. **An unproven claim presented as fact.**
   - What happened: Claude stated a Room "can hold at most 96 bookings in a day", and used it to argue one page of 100 always holds a whole Day.
   - What I did: I rejected the claim and required the behaviour to be verified instead.
   - Result: the frontend follows every page, and tests check pagination with bookings that cross midnight.

2. **A rule the brief didn't ask for.**
   - What happened: Claude proposed that bookings cannot be cancelled once started.
   - What I did: I rejected it, because the brief's only rule is that the creator cancels.
   - Result: a Booker may cancel at any time (ADR 0002), and the README states this reading of the brief.

3. **An inflated performance claim.**
   - What happened: Claude reported, and wrote into commit `6916e89`, that its query change took the Day schedule from 9.7 ms to 0.057 ms.
   - Why it was wrong: its seed command had refreshed planner statistics only for the bookings table, so PostgreSQL believed there were 3 Rooms and chose a bad plan. The "before" figure was an artifact.
   - How it was caught: a review required every number to be backed by a saved plan, and re-measuring showed the discrepancy.
   - Result: the fair gain is 2–20×, measured three times with fresh statistics, and the evidence file states the correction.

4. **A security setting that broke the app, and two reviewers who disagreed.**
   - What happened: Claude's initial settings included an HTTPS redirect. With `DEBUG` off, it redirected every request to an HTTPS port nobody served.
   - What followed: one review removed it, then a security review argued for it again.
   - Result: it was restored and **documented** (`DEBUG=False` requires HTTPS, ADR 0004).
   - Lesson: the right answer needed a human decision about what "production-safe" means here.

5. **Unsafe or unverified actions by the agent.**
   - **A global cleanup command:** it ran `docker volume prune -f`, which affects every Docker project on the machine, not just this one. It reported this straight away, and I then forbade global Docker cleanup.
   - **A false "all clear":** a shell quoting error made three security searches fail while still printing "none found". It noticed, and re-ran them correctly before recording the results.
   - **An attack payload against the wrong code:** it ran an injection test against the old, vulnerable version of a development command. The test failed harmlessly inside a rolled-back transaction, and the command was then fixed.

Tests and reviews also caught bugs in AI-written code, each fixed with a test that failed first:
- simultaneous bookings that **deadlocked** into a `500` (the data stayed correct);
- a failed logout that looked successful;
- a `+03:00:30` offset slipping past the whole-minute rule;
- "Sept" instead of "Sep";
- tests that could never fail.

## A decision I made myself

I chose to use Matt Pocock's skills workflow because I wanted the AI agent to work in a structured, disciplined, and verifiable way instead of generating large amounts of code from broad instructions. I wanted the project to have clear requirements, documented architecture decisions, small implementation tickets, tests, code reviews, and incremental commits, with me reviewing each ticket before allowing the agent to continue.

I used ChatGPT to help plan and guide the project, and Claude Opus 5.5 through Claude Code to implement and test it. The skills workflow helped me organize the agent's work and made it easier to identify mistakes, challenge assumptions, and verify behavior.

I learned that using AI alone is not enough: the way we guide it, monitor its work, and independently verify its results matters just as much as the model's capabilities.
