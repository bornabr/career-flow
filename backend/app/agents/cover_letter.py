"""Cover letter generation agent — produces a tailored cover letter from CV + job description."""

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from app.services.llm import create_model_from_string

COVER_LETTER_SYSTEM_PROMPT = (
    "You are a senior career coach and executive-level cover letter specialist. "
    "You write persuasive, role-specific cover letters that complement the CV rather than repeating it line-by-line. "
    "Your writing must translate CV evidence into a coherent candidacy story for a specific role. "
    "Anti-hallucination is absolute: never invent, infer, embellish, or generalize beyond provided CV data and optional user instructions. "
    "Use a concrete, professional voice; avoid cliches, fluff, and generic templates."
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
    company_section = f"**Company Name**: {company_name}\n\n" if company_name else ""
    user_section = f"**Additional Instructions**:\n{user_instructions}\n\n" if user_instructions else ""
    sections = cv_data.get("sections", {})

    def _section_text(lines: list[str]) -> str:
        return chr(10).join(lines) if lines else "- Not provided"

    social_lines = [
        f"- {n.get('network', '')}: {n.get('username', '')} ({n.get('url', '')})"
        for n in cv_data.get("social_networks", [])
    ]
    summary_lines = [f"- {line}" for line in sections.get("Summary", [])]
    skills_lines = [f"- {s.get('label', '')}: {s.get('details', '')}" for s in sections.get("Skills", [])]

    experience_lines: list[str] = []
    for exp in sections.get("Experience", []):
        experience_lines.append(
            f"- Company: {exp.get('company', '')} | Position: {exp.get('position', '')} | "
            f"Location: {exp.get('location', '')} | Dates: {exp.get('start_date', '')} to {exp.get('end_date', '')}"
        )
        if exp.get("summary"):
            experience_lines.append(f"  Summary: {exp.get('summary', '')}")
        if exp.get("highlights"):
            experience_lines.append(f"  Highlights: {'; '.join(exp.get('highlights', []))}")

    education_lines = [
        f"- {e.get('degree', '')} in {e.get('area', '')} | {e.get('institution', '')} | "
        f"{e.get('start_date', '')} to {e.get('end_date', '')}"
        for e in sections.get("Education", [])
    ]

    project_lines: list[str] = []
    for p in sections.get("PersonalProjects", []) or []:
        project_lines.append(f"- {p.get('name', '')}: {p.get('summary', '')}")
        if p.get("highlights"):
            project_lines.append(f"  Highlights: {'; '.join(p.get('highlights', []))}")

    publication_lines = [
        f"- {p.get('title', '')} | Journal: {p.get('journal', '')}"
        for p in sections.get("Publications", []) or []
    ]

    cv_text = f"""Name: {cv_data.get('name', 'the candidate')}
Location: {cv_data.get('location', '')}
Email: {cv_data.get('email', '')}
Phone: {cv_data.get('phone', '')}
Website: {cv_data.get('website', '')}

Social Networks:
{_section_text(social_lines)}

Summary:
{_section_text(summary_lines)}

Experience:
{_section_text(experience_lines)}

Skills:
{_section_text(skills_lines)}

Education:
{_section_text(education_lines)}

Personal Projects:
{_section_text(project_lines)}

Publications:
{_section_text(publication_lines)}"""

    return f"""Write a professional cover letter for the following candidate and job posting.

Craft a compelling story of fit. Complement the CV by interpreting evidence and motivation, not by repeating bullet points.

**CRITICAL RULES:**
1. Anti-hallucination is mandatory: reference only facts explicitly present in the CV data below.
2. Never invent achievements, technologies, dates, credentials, responsibilities, or outcomes.
3. Connect 2-3 concrete CV achievements to specific job-description requirements.
4. Match tone and formality to the job posting.
5. Opening must name the target role and one standout CV-backed qualification.
6. Body paragraphs must use concise STAR mini-narratives from CV experience.
7. Closing must include a specific call to action tied to role priorities.
8. Keep total length between 250 and 350 words.

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
