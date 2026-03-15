from pydantic_ai import Agent

from app.agents.prompts import SYSTEM_PROMPT, build_tailor_prompt
from app.schemas.cv import CV
from app.services.llm import create_model_from_string

# Reusable agent — model is overridden per-request via run(model=...)
tailor_agent = Agent(
    "test",
    output_type=CV,
    system_prompt=SYSTEM_PROMPT,
)


async def tailor_cv(
    resume_text: str,
    job_description: str,
    model_name: str,
    api_key: str,
    user_instructions: str | None = None,
) -> CV:
    """Run the tailor agent to generate a structured CV from resume + job description."""
    model = create_model_from_string(model_name, api_key)
    prompt = build_tailor_prompt(resume_text, job_description, user_instructions)
    result = await tailor_agent.run(prompt, model=model)
    return result.output
