import json
from collections.abc import Mapping

from pydantic_ai import Agent

from app.agents.chat_prompts import REFINEMENT_SYSTEM_PROMPT
from app.schemas.chat import RefinementResult
from app.services.llm import create_model_from_string


refinement_agent = Agent(
    "test",
    output_type=RefinementResult,
    system_prompt=REFINEMENT_SYSTEM_PROMPT,
)


def build_refinement_prompt(
    current_cv_dict: Mapping[str, object],
    resume_text: str,
    job_description: str,
    user_message: str,
) -> str:
    formatted_cv = json.dumps(current_cv_dict, indent=2, sort_keys=True, ensure_ascii=False)

    return f"""
Use the context below to process one CV refinement turn and return structured JSON only.

Refinement rules:
- Apply only the user's requested edits.
- Preserve all unmodified fields exactly as they are unless a direct change is requested.
- Keep the assistant_reply concise and explicit about what changed.
- If the request is ambiguous, ask a clarifying question in assistant_reply and make only the safest minimal update.
- Only use information from the original resume text. Do not add unsupported facts.

Latest user refinement request:
{user_message}

Current CV dictionary:
{formatted_cv}

Original resume text (source of truth):
{resume_text}

Job description (context only; never a source for new facts):
{job_description}
"""


async def run_refinement_turn(
    current_cv_dict: Mapping[str, object],
    resume_text: str,
    job_description: str,
    user_message: str,
    model_name: str,
    api_key: str,
) -> RefinementResult:
    model = create_model_from_string(model_name, api_key)
    prompt = build_refinement_prompt(
        current_cv_dict=current_cv_dict,
        resume_text=resume_text,
        job_description=job_description,
        user_message=user_message,
    )
    result = await refinement_agent.run(prompt, model=model)
    return result.output
