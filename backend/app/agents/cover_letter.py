"""Cover letter generation agent — produces a tailored cover letter from CV + job description."""

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from app.services.llm import create_model_from_string

COVER_LETTER_SYSTEM_PROMPT = (
    "You are an expert career coach and professional writer. Your goal is to write compelling, "
    "personalized cover letters that complement a candidate's CV for a specific job posting. "
    "You must NEVER hallucinate or invent information. Only reference experiences, skills, and "
    "achievements that are present in the provided CV data. Write in a professional but natural tone — "
    "avoid generic filler phrases and clichés."
)


class CoverLetter(BaseModel):
    """Structured cover letter output."""

    greeting: str = Field(
        ...,
        description="Opening greeting (e.g., 'Dear Hiring Manager,' or 'Dear [Name],')",
    )
    opening: str = Field(
        ...,
        description="Opening paragraph: state the role, express enthusiasm, and hook the reader with a standout qualification.",
    )
    body: list[str] = Field(
        ...,
        description="1-2 body paragraphs. Each maps specific CV achievements to job requirements. Use concrete examples.",
    )
    closing: str = Field(
        ...,
        description="Closing paragraph: reiterate fit, express enthusiasm, and include a call to action.",
    )
    sign_off: str = Field(
        default="Sincerely,",
        description="Sign-off phrase (e.g., 'Sincerely,', 'Best regards,')",
    )


# Reusable agent — model overridden per request via run(model=...)
cover_letter_agent = Agent(
    "test",
    output_type=CoverLetter,
    system_prompt=COVER_LETTER_SYSTEM_PROMPT,
)


def _build_cover_letter_prompt(
    cv_data: dict,
    job_description: str,
    company_name: str | None = None,
    user_instructions: str | None = None,
) -> str:
    """Build the user prompt for cover letter generation."""
    company_section = ""
    if company_name:
        company_section = f"**Company Name**: {company_name}\n\n"

    user_section = ""
    if user_instructions:
        user_section = f"**Additional Instructions**:\n{user_instructions}\n\n"

    # Format CV data as readable text for the prompt
    name = cv_data.get("name", "the candidate")
    sections = cv_data.get("sections", {})

    summary = " ".join(sections.get("Summary", []))
    experience_lines = []
    for exp in sections.get("Experience", []):
        role = f"{exp.get('position', '')} at {exp.get('company', '')}"
        highlights = "; ".join(exp.get("highlights", []))
        experience_lines.append(f"- {role}: {highlights}")

    skills_lines = []
    for skill in sections.get("Skills", []):
        skills_lines.append(f"- {skill.get('label', '')}: {skill.get('details', '')}")

    cv_text = f"""Name: {name}
Summary: {summary}

Experience:
{chr(10).join(experience_lines)}

Skills:
{chr(10).join(skills_lines)}"""

    return f"""Write a professional cover letter for the following candidate and job posting.

**CRITICAL RULES:**
1. Only reference experiences, skills, and achievements present in the CV data below.
2. Do NOT invent or exaggerate any information.
3. Keep the letter concise — aim for 250-350 words total.
4. Match the tone and language of the job description.
5. Highlight 2-3 specific achievements from the CV that directly address key job requirements.

{company_section}{user_section}**Candidate CV Data**:
{cv_text}

---
**Job Description**:
{job_description}
---
"""


async def generate_cover_letter(
    cv_data: dict,
    job_description: str,
    model_name: str,
    api_key: str,
    company_name: str | None = None,
    user_instructions: str | None = None,
) -> CoverLetter:
    """Run the cover letter agent to generate a structured cover letter."""
    model = create_model_from_string(model_name, api_key)
    prompt = _build_cover_letter_prompt(cv_data, job_description, company_name, user_instructions)
    result = await cover_letter_agent.run(prompt, model=model)
    return result.output
