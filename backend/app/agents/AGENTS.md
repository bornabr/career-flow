# AI AGENTS

Pydantic AI agents for CV tailoring, multi-agent review, synthesis, validation, and cover letter generation.

## OVERVIEW

Seven AI agents + one orchestrator with a shared pattern: create `Agent` once with placeholder model, override model per-request via `run(model=...)`. All agents use structured output (Pydantic `output_type`). The pipeline supports two modes:

- **Standard**: Tailor → Validator → done
- **Review**: Tailor → 3 parallel reviewers + optional hallucination check → Synthesis → Validator → done

## PIPELINE FLOW

```
                         ┌──────────────────┐
                         │   Tailor Agent    │
                         │ (resume + JD →   │
                         │   draft CV)       │
                         └────────┬─────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │ review_mode │             │
                    │ = false     │ = true      │
                    ▼             ▼             │
              ┌──────────┐  ┌────────────────┐  │
              │ Validator │  │  asyncio.gather │  │
              │ (done)    │  │  ┌───────────┐ │  │
              └──────────┘  │  │ HR Review  │ │  │
                            │  ├───────────┤ │  │
                            │  │ Tech Review│ │  │
                            │  ├───────────┤ │  │
                            │  │ ATS Review │ │  │
                            │  ├───────────┤ │  │
                            │  │ Halluc.Chk │ │  │
                            │  │ (optional) │ │  │
                            │  └───────────┘ │  │
                            └───────┬────────┘  │
                                    ▼           │
                            ┌──────────────┐    │
                            │  Synthesis   │    │
                            │ (draft + all │    │
                            │  reviews →   │    │
                            │  refined CV) │    │
                            └──────┬───────┘    │
                                   ▼            │
                            ┌──────────────┐    │
                            │  Validator   │    │
                            │  (done)      │    │
                            └──────────────┘    │
```

## FILES

| File | Type | Purpose |
|------|------|---------|
| `pipeline.py` | Orchestrator | Coordinates all agents — `generate_cv_standard()` and `generate_cv_with_review()` |
| `tailor.py` | AI Agent | Main CV generation — takes resume + JD → structured `CV` |
| `hr_reviewer.py` | AI Agent | HR reviewer — career progression, role alignment, cultural fit, red flags |
| `technical_reviewer.py` | AI Agent | Technical reviewer — technical depth, stack relevance, project credibility |
| `ats_reviewer.py` | AI Agent | ATS optimizer — keyword coverage, placement, formatting compliance |
| `synthesis.py` | AI Agent | Synthesis — takes CV draft + ReviewMemos + resume + JD → refined `CV` |
| `hallucination_checker.py` | AI Agent | AI hallucination detection — compares CV against original resume text |
| `validator.py` | Deterministic | Post-generation validation: fuzzy hallucination detection, ATS cleaning, null removal |
| `cover_letter.py` | AI Agent | Cover letter generation — takes CV data + JD → structured `CoverLetter` |
| `prompts.py` | Prompts | System prompt + user prompt builder for the tailor agent |

## AGENT PATTERN

```python
# 1. Define agent once at module level with placeholder model
agent = Agent("test", output_type=MySchema, system_prompt=SYSTEM_PROMPT)

# 2. Create real model per-request using services/llm.py factory
model = create_model_from_string(model_name, api_key)

# 3. Run with real model
result = await agent.run(prompt, model=model)
return result.output
```

## REVIEW COMMITTEE PATTERN

Reviewer agents evaluate the CV draft independently, each from their specialized perspective. Their `ReviewMemo` outputs contain scores, findings, and recommendations. The Synthesis agent receives all memos and produces a refined CV.

```python
# Reviewers run in parallel via asyncio.gather
reviews = await asyncio.gather(
    review_as_hr(cv_dict, jd, model, key),
    review_as_technical(cv_dict, jd, model, key),
    review_as_ats(cv_dict, jd, model, key),
    return_exceptions=True,
)

# Synthesis uses reviews to refine the CV
refined_cv = await synthesize_cv(cv_dict, reviews, resume_text, jd, model, key)
```

## VALIDATION LAYERS

1. **Deterministic (`validator.py`)**: Fuzzy string matching (SequenceMatcher sliding window), synonym-aware comparison (~50 tech synonyms), numeric claim detection (percentages, dollar amounts, multipliers), company/position verification against resume text.
2. **AI-powered (`hallucination_checker.py`)**: Semantic comparison of CV content against original resume. Catches paraphrased hallucinations that string matching misses. Runs in parallel with reviewers during review mode.

## CRITICAL RULES

**Anti-hallucination is the #1 constraint across all agents.**

- NEVER add information not present in source documents.
- NEVER infer, guess, or synthesize content from job descriptions.
- Omit missing fields — do not fill gaps.
- Bold/emphasize job description keywords ONLY if they exist in source documents.
- Cover letter: only reference experiences present in the CV data.
- Synthesis agent: may reorder, rephrase, and restructure — but must NOT add new facts.

## ANTI-PATTERNS

- **DO NOT** create agents that add content from job descriptions to the CV — source documents are the single source of truth.
- **DO NOT** instantiate agents with real models at module level — models are resolved per-request for multi-provider support.
- **DO NOT** call LLM providers directly — use `services/llm.py` `create_model_from_string()`.
- **DO NOT** call agents directly from API routes — use `pipeline.py` orchestration functions.
- **DO NOT** use camelCase for CV data dict keys — the CV schema uses snake_case (`start_date`, `end_date`, not `startDate`, `endDate`).

## NOTES

- `validator.py` is a deterministic module (no LLM calls) — uses fuzzy matching, synonym tables, and regex for hallucination/ATS checks.
- `hallucination_checker.py` IS an AI agent — it uses an LLM for semantic comparison and outputs `HallucinationReport`.
- Prompt engineering lives in `prompts.py` for the tailor agent, but inline in other agent files (cover_letter, reviewers, synthesis, hallucination_checker).
- The `CoverLetter` Pydantic model is defined locally in `cover_letter.py`, not in `schemas/`.
- Review schemas (`ReviewMemo`, `HallucinationReport`, `ReviewPanelResult`) live in `schemas/review.py`.
- Reviewer failures are handled gracefully — if one reviewer fails, the others' results are still used for synthesis.
- The review model can differ from the main generation model (e.g., `gemini-2.5-flash` for reviews, `gemini-2.5-pro` for generation).
