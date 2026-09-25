# Career-Flow Phase 2: Outputs

## Scope

Implement the four output flows in the design spec: tailored resumes, cover letters and short bios, interview prep, and outreach. Keep career data in the separate private repo. Generated output belongs under that repo's `outputs/` directory. No flow sends messages or publishes material.

## Work

1. Add a reusable, single-column Typst resume template and a synthetic example. The resume skill supports both general resumes (optional target role, no posting) and posting-tailored resumes. It selects evidence from `data/INDEX.md` and source entities, records its selection rationale, compiles a PDF, checks its extracted text and visual layout, and logs a variant only when it was actually used for an application.
2. Add deterministic resume PDF checks for parsing, expected section order, and required posting terms. Make failures actionable so the agent can revise and recompile.
3. Add cover-letter, interview-prep, and outreach skills with source-id provenance and private output paths. Outreach drafts only; a read-only helper lists follow-ups due from application records.
4. Tighten validation of application-log fields and document the generated output layout and required local tools.
5. Test schema and helper edge cases, compile the synthetic resume, inspect the resulting PDF, run the full suite, and exercise the due-follow-up helper on synthetic records.

## Acceptance

- The synthetic resume compiles with Typst, contains extractable text in expected order, and passes both the general PDF check (no posting keywords) and the tailored ATS helper check.
- Deliberately missing sections or keywords fail the ATS helper; malformed follow-up fields fail validation.
- The four skills are discoverable in both plugin hosts and give executable, privacy-preserving instructions.
- The full plugin test suite passes. A real-data acceptance run follows before Phase 3.
