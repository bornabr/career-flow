from typing import Union

from pydantic_ai import Agent

from app.agents.chat_prompts import INTAKE_SYSTEM_PROMPT
from app.schemas.chat import ChatMessage, IntakeTurnResult
from app.services.llm import create_model_from_string


intake_agent = Agent(
    "test",
    output_type=IntakeTurnResult,
    system_prompt=INTAKE_SYSTEM_PROMPT,
)


ConversationItem = Union[ChatMessage, dict[str, str]]


def _format_conversation_history(conversation_history: list[ConversationItem]) -> str:
    if not conversation_history:
        return "No prior conversation."

    lines: list[str] = []
    for idx, message in enumerate(conversation_history, start=1):
        if isinstance(message, ChatMessage):
            role = message.role
            content = message.content
        else:
            role = str(message.get("role", "unknown"))
            content = str(message.get("content", "")).strip()

        if not content:
            continue

        lines.append(f"{idx}. {role}: {content}")

    return "\n".join(lines) if lines else "No prior conversation."


def build_intake_prompt(
    conversation_history: list[ConversationItem],
    resume_text: str,
    job_description: str,
    user_instructions: Union[str, None] = None,
) -> str:
    instructions = user_instructions.strip() if user_instructions else "None"
    history = _format_conversation_history(conversation_history)

    return f"""
Use the intake conversation context below and return structured JSON only.

Rules for this turn:
- Ask exactly one clarifying question if context is missing.
- Do not ask multiple questions.
- If enough context exists, set ready_to_generate=true and do not ask another question.
- Populate extracted_constraints with concise user constraints.
- Populate missing_fields with concise labels for unresolved critical information.

Known priority topics:
1) Page count preference
2) Emphasis areas
3) Exclusions/de-emphasis preferences

Conversation history:
{history}

User instructions:
{instructions}

Resume text:
{resume_text}

Job description:
{job_description}
"""


async def run_intake_turn(
    conversation_history: list[ConversationItem],
    resume_text: str,
    job_description: str,
    model_name: str,
    api_key: str,
    user_instructions: Union[str, None] = None,
) -> IntakeTurnResult:
    model = create_model_from_string(model_name, api_key)
    prompt = build_intake_prompt(
        conversation_history=conversation_history,
        resume_text=resume_text,
        job_description=job_description,
        user_instructions=user_instructions,
    )
    result = await intake_agent.run(prompt, model=model)
    return result.output
