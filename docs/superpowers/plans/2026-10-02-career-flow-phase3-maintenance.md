# Career-Flow Phase 3: Maintenance cadence

## Scope

Add the two manual maintenance skills from the design (`checkin` and `maintain`),
a read-only status report, and two opt-in passive candidate sources. Correct the
Phase 2 acceptance finding: exploratory outreach must not create an application.
The separate career-data repo remains private; candidates never become claims
without user review.

## Work

1. Report check-in due date, pending inbox count, staleness, `needs-metrics`,
   possible duplicate skill/story titles, schema/link issues, and index drift.
2. Guide a check-in across the period since the previous approved check-in. Store
   the cadence marker at `data/checkins/YYYY-MM-DD.md` only after approval.
3. Guide maintenance edits with explicit review, raw-note preservation, link repair,
   validation, and no silent deletion.
4. Add a default-off GitHub merged-PR scanner restricted to named repositories and
   a default-off Claude Code SessionEnd hook restricted to named project paths.
   Both add only deduplicated inbox candidates. Do not copy transcript text.
5. Test disabled/no-allowlist behavior, source filtering, deduplication, reporting,
   and plugin discovery. Run the full plugin suite and a private-repo read-only
   status smoke test; do not enable passive capture in the user's data repo.

## Acceptance

- Both skills are discoverable in plugin hosts and give actionable, privacy-bound
  instructions.
- Passive capture does not write when disabled, missing an allowlist, or given an
  unlisted session workspace. It never creates an entity, commit, or outbound message.
- Repeated source scans do not duplicate an inbox candidate.
- Status reporting does not alter a data repo and handles malformed entries by
  surfacing errors rather than hiding them.
- Draft-only outreach leaves `data/applications/` untouched.
