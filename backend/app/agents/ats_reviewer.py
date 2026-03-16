from pydantic_ai import Agent

from app.schemas.review import ReviewMemo
from app.services.llm import create_model_from_string

ATS_SYSTEM_PROMPT = """You are an ATS (Applicant Tracking System) optimization specialist with deep expertise in resume parsing
algorithms, keyword matching systems, and recruitment technology. You evaluate resumes for maximum
compatibility with automated screening systems while maintaining human readability. You return structured
JSON feedback according to the provided schema. You must NEVER hallucinate -- only reference content
present in the CV and job description."""


def _format_cv_data_for_prompt(cv_data: dict[str, object]) -> str:
    lines: list[str] = []

    for key, value in cv_data.items():
        if key == "sections" and isinstance(value, dict):
            lines.append("Sections:")
            for section_name, section_value in value.items():
                lines.append(f"\n{section_name}:")
                lines.extend(_format_section_value(section_value, indent=2))
        else:
            lines.append(f"{key}:")
            lines.extend(_format_section_value(value, indent=2))

    return "\n".join(lines)


def _format_section_value(value: object, indent: int = 0) -> list[str]:
    prefix = " " * indent

    if isinstance(value, dict):
        lines: list[str] = []
        for nested_key, nested_value in value.items():
            lines.append(f"{prefix}{nested_key}:")
            lines.extend(_format_section_value(nested_value, indent=indent + 2))
        return lines

    if isinstance(value, list):
        lines = []
        if not value:
            return [f"{prefix}- (none)"]

        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}-")
                lines.extend(_format_section_value(item, indent=indent + 2))
            else:
                lines.append(f"{prefix}- {item}")
        return lines

    if value in (None, ""):
        return [f"{prefix}(empty)"]

    return [f"{prefix}{value}"]


def _build_ats_review_prompt(cv_data: dict[str, object], job_description: str) -> str:
    cv_text = _format_cv_data_for_prompt(cv_data)

    return f"""**Your Role**: ATS Optimization Specialist reviewing a candidate's tailored CV for maximum automated screening compatibility.

**Evaluation Criteria** (assess each):
1. **Keyword Coverage** -- Extract the top 10-15 critical keywords/phrases from the JD (job titles, required skills, tools, certifications). For each, note whether it appears in the CV verbatim, as a synonym, or is missing entirely. Calculate an approximate keyword match percentage.
2. **Keyword Placement** -- Are the most important keywords placed in high-impact positions? (Summary > Experience highlights > Skills section). Keywords buried in older roles or education are less effective.
3. **Section Structure** -- Does the CV have clearly labeled, ATS-parseable sections? Standard section names (Experience, Education, Skills, Summary) parse better than creative alternatives.
4. **Formatting Compliance** -- Check for ATS-unfriendly elements: special characters, unicode symbols, tables, columns, headers/footers, images. Note any that would cause parsing failures.
5. **Semantic Match** -- Beyond exact keywords, does the CV's language semantically align with the JD? For example, "built microservices" matches "microservices architecture experience" even without exact phrase match.
6. **Density & Distribution** -- Are keywords naturally distributed throughout the CV or unnaturally stuffed into one section? Natural distribution scores higher.

**Scoring Guide**:
- 9-10: Excellent ATS optimization, >85% keyword coverage, clean formatting
- 7-8: Good optimization, 70-85% keyword coverage, minor issues
- 5-6: Moderate optimization, 50-70% keyword coverage, some formatting concerns
- 3-4: Poor optimization, <50% keyword coverage, significant issues
- 1-2: Would likely be filtered out by most ATS systems

**Set reviewer_role to "ats" in your output.**

**CRITICAL**: Do NOT recommend adding keywords or skills not present in the CV. You can only suggest better placement, phrasing, or emphasis of existing content to improve ATS compatibility.

**Candidate CV Data**:
{cv_text}

---
**Job Description**:
{job_description}
---
"""


ats_reviewer_agent = Agent(
    "test",
    output_type=ReviewMemo,
    system_prompt=ATS_SYSTEM_PROMPT,
)


async def review_as_ats(cv_data: dict, job_description: str, model_name: str, api_key: str) -> ReviewMemo:
    model = create_model_from_string(model_name, api_key)
    prompt = _build_ats_review_prompt(cv_data, job_description)
    result = await ats_reviewer_agent.run(prompt, model=model)
    return result.output
