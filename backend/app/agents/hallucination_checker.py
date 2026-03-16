from pydantic_ai import Agent

from app.schemas.review import HallucinationReport
from app.services.llm import create_model_from_string

HALLUCINATION_SYSTEM_PROMPT = """
You are a factual accuracy auditor for generated CVs.
Your only job is to compare generated CV content against source resume text and detect fabricated or embellished claims.
Do not evaluate writing quality, style, or competitiveness.

Check every CV claim against the resume.
- Company names, job titles, dates, education details, personal info: exact match required.
- Skills: must appear in resume or be reasonably inferred from explicitly described work.
- Quantified metrics (numbers, percentages, counts, timelines): must be present in source.
- Project names and project descriptions: must be supported by source.
- Legitimate rephrasing with same meaning must not be flagged.

Classification:
- hard hallucination (fabricated fact) -> confidence "high"
- soft hallucination (embellishment) -> confidence "medium"
- uncertain mismatch -> confidence "low"

For each hallucination include field_path, hallucinated_content, confidence, and reasoning.
Output must strictly match HallucinationReport.
""".strip()

hallucination_agent = Agent(
    "test",
    output_type=HallucinationReport,
    system_prompt=HALLUCINATION_SYSTEM_PROMPT,
)


def _format_cv_data_for_prompt(cv_data: dict[str, object]) -> str:
    lines: list[str] = ["Generated CV Data:"]

    top_fields = ["name", "location", "email", "phone", "website"]
    for key in top_fields:
        value = cv_data.get(key)
        lines.append(f"- {key}: {value if value else '[missing]'}")

    social_networks_raw = cv_data.get("social_networks")
    social_networks = social_networks_raw if isinstance(social_networks_raw, list) else []
    lines.append("- social_networks:")
    if social_networks:
        for index, social in enumerate(social_networks):
            network = social.get("network", "") if isinstance(social, dict) else ""
            username = social.get("username", "") if isinstance(social, dict) else ""
            lines.append(f"  - [{index}] network={network}, username={username}")
    else:
        lines.append("  - [none]")

    sections_raw = cv_data.get("sections")
    sections = sections_raw if isinstance(sections_raw, dict) else {}
    section_names = ["Summary", "Skills", "Experience", "Education", "AdditionalExperience", "Publications", "PersonalProjects"]

    for section_name in section_names:
        section_value = sections.get(section_name)
        lines.append(f"- sections.{section_name}:")

        if not section_value:
            lines.append("  - [none]")
            continue

        if isinstance(section_value, list):
            for index, item in enumerate(section_value):
                if isinstance(item, dict):
                    lines.append(f"  - [{index}]")
                    for field, field_value in item.items():
                        rendered = _render_field_value(field_value)
                        lines.append(f"    - {field}: {rendered}")
                else:
                    lines.append(f"  - [{index}] {_render_field_value(item)}")
        else:
            lines.append(f"  - {_render_field_value(section_value)}")

    return "\n".join(lines)


def _render_field_value(value: object) -> str:
    if value is None:
        return "[none]"
    if isinstance(value, list):
        return "; ".join(str(item) for item in value) if value else "[empty]"
    if isinstance(value, dict):
        return ", ".join(f"{k}={v}" for k, v in value.items()) if value else "[empty]"
    return str(value)


def _build_hallucination_prompt(cv_data: dict[str, object], original_resume: str) -> str:
    formatted_cv = _format_cv_data_for_prompt(cv_data)
    return f"""
Audit the generated CV against the source resume text.

Check EVERY claim in the CV. Validate all of the following:
1) Company names, job titles, start_date/end_date: exact match required.
2) Skills: must appear in source resume or be reasonably inferred from described work.
3) Quantified metrics (numbers, percentages, counts, durations): must be present in source.
4) Project names and project descriptions: must match source.
5) Education details (institution, area, degree, dates): exact match required.
6) Personal info (name, email, phone): must match source.

Flag only unsupported facts. Do NOT flag legitimate rephrasing with same meaning.
Use confidence levels:
- high: hard hallucination (fabricated fact)
- medium: soft hallucination (likely embellishment)
- low: uncertain mismatch

Return a HallucinationReport with:
- has_hallucinations: bool
- items: list of hallucinations, each with field_path, hallucinated_content, confidence, reasoning
- summary: concise assessment

{formatted_cv}

Original Resume Text (Ground Truth):
{original_resume}
""".strip()


async def check_hallucinations_ai(
    cv_data: dict[str, object],
    original_resume: str,
    model_name: str,
    api_key: str,
) -> HallucinationReport:
    model = create_model_from_string(model_name, api_key)
    prompt = _build_hallucination_prompt(cv_data, original_resume)
    result = await hallucination_agent.run(prompt, model=model)
    return result.output
