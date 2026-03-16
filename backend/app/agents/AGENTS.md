# AI AGENTS

Pydantic AI agents for CV tailoring, validation, and cover letter generation.

## OVERVIEW

Three agents with a shared pattern: create `Agent` once with placeholder model, override model per-request via `run(model=...)`. All use structured output (Pydantic `output_type`).

## FILES

| File | Purpose |
|------|---------|
| `tailor.py` | Main CV generation agent — takes resume + job description → structured `CV` |
| `validator.py` | Post-generation validation: ATS cleaning, hallucination detection, null section removal |
| `cover_letter.py` | Cover letter agent — takes CV data + job description → structured `CoverLetter` |
| `prompts.py` | System prompt + user prompt builder for the tailor agent |

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

## CRITICAL RULES

**Anti-hallucination is the #1 constraint across all agents.**

- NEVER add information not present in source documents.
- NEVER infer, guess, or synthesize content from job descriptions.
- Omit missing fields — do not fill gaps.
- Bold/emphasize job description keywords ONLY if they exist in source documents.
- Cover letter: only reference experiences present in the CV data.

## ANTI-PATTERNS

- **DO NOT** create agents that add content from job descriptions to the CV — source documents are the single source of truth.
- **DO NOT** instantiate agents with real models at module level — models are resolved per-request for multi-provider support.
- **DO NOT** call LLM providers directly — use `services/llm.py` `create_model_from_string()`.

## NOTES

- `validator.py` is NOT an AI agent — it's deterministic Python (string matching for hallucination checks, regex for ATS cleaning).
- Prompt engineering lives in `prompts.py` for the tailor agent, but inline in `cover_letter.py` for the cover letter agent.
- The `CoverLetter` Pydantic model is defined locally in `cover_letter.py`, not in `schemas/`.
