---
name: resume
description: Use when creating a general resume or CV from private career data, with or without a target role, or tailoring one to a job posting; compiles and checks a Typst PDF and tracks variants actually used for applications
---

# Resume — general or posting-tailored PDF

## Resolve resources and data

Resolve `<plugin-root>` from this SKILL.md path (two directories above), or from the
expanded `${CLAUDE_PLUGIN_ROOT}` in Claude Code. Verify that
`templates/resume/layout.typ`, `templates/resume/example.typ`,
`scripts/check_resume.py`, and `scripts/validate.py` exist. Never run unresolved
placeholders or save a host-specific plugin path.

Use the current directory as `<data-repo>` if it contains `config.yaml` and `data/`;
otherwise read `data_repo:` from `~/.config/career-flow/config`. Stop with bootstrap
instructions if neither is valid. Pull before writing; if the worktree is dirty or
pull conflicts, identify the existing changes and avoid overwriting them. Read
`data/INDEX.md`, `data/profile.md`, and `config.yaml` before selecting entities.

## Flow

1. **Setup interview, before drafting.** Always ask the user a few concise questions
   (normally 2-4, grouped together) about the resume's target, length/style, which
   roles or projects to include or exclude, and what work within those roles to
   emphasize. Ask how ambiguous titles or overlapping roles should appear, rather
   than silently combining them or adding labels such as "promoted from intern."
   Check whether sensitive current-employer details and metrics are suitable for
   external use. Do not repeat facts already answered in the request; use those
   answers and ask about the remaining material choices. Wait for answers before
   finalizing the selection and draft.
2. Choose the mode from the user's request. A supplied job posting means **tailored**
   mode: get the posting text or URL, company, and role. Fetch a live URL and retain
   its URL and access date; if unavailable, ask for pasted text. Without a posting,
   use **general** mode. A target role or field is optional: use one the user gives,
   otherwise use the preferences and headline in `data/profile.md`. If those point
   in several materially different directions, ask which to emphasize; if they are
   blank, create a broad career overview. Never require a posting for general mode.
   Respect any requested page length; otherwise aim for a concise resume.
3. Select source entities from the index, then read each selected file including
   `## Raw notes`. In tailored mode, map posting requirement → source id → exact
   supported claim and identify must-have terms. In general mode, choose the
   strongest current, quantified, broadly relevant evidence (or evidence relevant
   to the optional target role); map each claim to its source id and record why it
   was selected. Include a balanced, reverse chronological career history rather
   than trying to imply fit for an unspecified job. In both modes, respect the
   user's attribution, dates, metrics, and `flags: [needs-metrics]`; never invent a
   figure or silently upgrade a tentative claim. Shape each experience entry so the
   bullets explain the person's actual work: domain, ownership, methods or tools,
   collaboration, and outcomes where supported. Give each bullet one clear work
   thread, with a readable subject, action, and purpose or result. Do not join
   unrelated accomplishments with a semicolon or a list of tools just to save space;
   split them or select the stronger claim. A metric belongs directly beside the
   specific action or system it measures, with enough context to make the relationship
   unambiguous. Metrics strengthen selected bullets; do not turn every bullet into a
   number or a miniature STAR story. Every included experience needs at least two
   distinct, supported bullets. A new role may have just two; longer or more relevant
   roles can have more. If only one substantive bullet is supported, ask for more
   detail or omit the role rather than padding it. Preserve the user's include/exclude
   and title choices.
4. Create `outputs/resumes/<company>-<role>-<YYYY-MM-DD>/` for tailored mode, or
   `outputs/resumes/general-<focus>-<YYYY-MM-DD>/` for general mode
   (`general-<YYYY-MM-DD>` if there is no focus). Use short lowercase hyphenated
   names. Copy `templates/resume/layout.typ` and `example.typ` there, rename the latter to
   `resume.typ`, and replace every synthetic claim with selected real evidence.
   Keep the single-column structure and reverse chronological experience order.
   Put grouped Skills immediately after Summary. Use a few meaningful groups (for
   example ML & Modeling, Engineering, Platforms) with only verified skills. Use
   content blocks in Typst for Summary and experience bullets so one or two key
   phrases can be bolded selectively; do not bold every metric or whole sentences.
   Read the bullets consecutively within each role: they should move naturally from
   what the person worked on to a distinct method, responsibility, or outcome, without
   abrupt topic shifts or repeated claims. Trim weaker content before shrinking type
   or cramming independent work into one line. Keep each section rule visually close
   to its heading.
   Education must show both start and end dates from the source entries. Include only
   sections with supported content. For each selected publication, use its verified
   paper URL and any verified code repository URL (`url` and `code_url` fields in the
   entity). If the entity lacks them, inspect the author's/publication's official
   pages for the links; do not guess. Render clickable Paper and Code labels when
   the links exist. Save the evidence
   map, source ids, omissions, mode, optional focus, and selection rationale as
   `tailoring.md`. Save `posting.md` only in tailored mode; in general mode, explicitly
   record that no posting was supplied.
5. Compile from that directory: `typst compile resume.typ resume.pdf`. If Typst is
   missing, ask the user to install it or install it with their authorization; do not
   claim a PDF exists. Inspect the PDF visually by rendering pages with `pdftoppm`.
   Fix clipping, crowding, malformed links, and awkward page breaks before delivery.
6. Run `python3 <plugin-root>/scripts/check_resume.py resume.pdf` with `--section`
   for every included heading in displayed order. In tailored mode, also pass
   `--keyword` for each truly required posting term supported by the user's evidence,
   and write `--json ats-check.json`. If a missing term cannot be claimed honestly,
   record the gap in `tailoring.md` instead of inserting an unsupported keyword. In
   general mode, pass **no** posting keywords and write `--json pdf-check.json`;
   describe the result as a PDF readability and structure check, not an ATS match to
   an unknown posting. Pass `--url` for each expected paper/code link, and verify
   that the compiled PDF contains those clickable destinations. Both modes must show
   a parseable PDF, extractable text, and proper heading order. Read the extracted
   text yourself for lost or scrambled
   text. Recompile and rerun checks after edits.
7. Show the PDF and selection rationale to the user. Creating a variant alone does
   not mean it was submitted. Only after the user says it was used for an application,
   create or update `data/applications/app-<company>-<date>.md` from the application
   template and set `resume_variant` to the repo-relative PDF path. Preserve the
   posting, if any, and the user's original application notes under `## Raw notes`.
8. Validate the data repo with `<plugin-root>/scripts/validate.py <data-repo>`, fix
   errors, and review the diff. Commit and push the output and any application entry
   when the user has approved the final draft. Do not commit copied synthetic claims.

## Rules

- Keep all artifacts in the private data repo; default application visibility to private.
- Do not fabricate career facts, use unsourced posting language as a career claim, or
  claim ATS compatibility beyond the checks performed. A general resume has no
  posting-specific keyword result.
- A resume variant path records actual use, not merely generation.
