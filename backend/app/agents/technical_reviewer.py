from pydantic_ai import Agent

from app.schemas.review import ReviewMemo
from app.services.llm import create_model_from_string

TECHNICAL_REVIEWER_SYSTEM_PROMPT = (
    "You are a Senior Technical Lead and Engineering Manager with 15+ years of experience in software engineering, "
    "system design, and technical hiring. You evaluate resumes from a technical perspective, assessing the depth "
    "and authenticity of technical claims, the relevance of technologies to the job requirements, and the "
    "credibility of project descriptions. You return structured JSON feedback according to the provided schema. "
    "You must NEVER hallucinate — only reference content present in the CV and job description."
)


technical_reviewer_agent = Agent(
    "test",
    output_type=ReviewMemo,
    system_prompt=TECHNICAL_REVIEWER_SYSTEM_PROMPT,
)


def _format_cv_data_for_prompt(cv_data: dict[str, object]) -> str:
    name = cv_data.get("name", "the candidate")
    sections_raw = cv_data.get("sections", {})
    sections = sections_raw if isinstance(sections_raw, dict) else {}

    summary = " ".join(sections.get("Summary", []))

    experience_lines = []
    for exp in sections.get("Experience", []):
        if not isinstance(exp, dict):
            continue
        role = f"{exp.get('position', '')} at {exp.get('company', '')}".strip()
        highlights = "; ".join(exp.get("highlights", []))
        experience_lines.append(f"- {role}: {highlights}")

    additional_experience_lines = []
    for exp in sections.get("AdditionalExperience", []) or []:
        if not isinstance(exp, dict):
            continue
        role = f"{exp.get('position', '')} at {exp.get('company', '')}".strip()
        highlights = "; ".join(exp.get("highlights", []))
        additional_experience_lines.append(f"- {role}: {highlights}")

    skills_lines = []
    for skill in sections.get("Skills", []):
        if not isinstance(skill, dict):
            continue
        skills_lines.append(f"- {skill.get('label', '')}: {skill.get('details', '')}")

    education_lines = []
    for edu in sections.get("Education", []):
        if not isinstance(edu, dict):
            continue
        degree = edu.get("degree") or ""
        area = edu.get("area") or ""
        institution = edu.get("institution") or ""
        summary_text = edu.get("summary") or ""
        highlights = "; ".join(edu.get("highlights", []) or [])
        line = f"- {degree} {area} at {institution}".strip()
        details = "; ".join(part for part in [summary_text, highlights] if part)
        if details:
            line = f"{line}: {details}"
        education_lines.append(line)

    personal_project_lines = []
    for project in sections.get("PersonalProjects", []) or []:
        if not isinstance(project, dict):
            continue
        project_name = project.get("name", "")
        project_summary = project.get("summary", "")
        project_highlights = "; ".join(project.get("highlights", []) or [])
        details = "; ".join(part for part in [project_summary, project_highlights] if part)
        personal_project_lines.append(f"- {project_name}: {details}")

    publications_lines = []
    for publication in sections.get("Publications", []) or []:
        if not isinstance(publication, dict):
            continue
        title = publication.get("title", "")
        journal = publication.get("journal", "")
        date = publication.get("date", "")
        authors = ", ".join(publication.get("authors", []))
        publications_lines.append(f"- {title} ({journal}, {date}) — Authors: {authors}")

    cv_parts = [
        f"Name: {name}",
        f"Summary: {summary}",
        "",
        "Experience:",
        "\n".join(experience_lines) if experience_lines else "- None provided",
        "",
        "Skills:",
        "\n".join(skills_lines) if skills_lines else "- None provided",
        "",
        "Education:",
        "\n".join(education_lines) if education_lines else "- None provided",
    ]

    if additional_experience_lines:
        cv_parts.extend(["", "Additional Experience:", "\n".join(additional_experience_lines)])

    if personal_project_lines:
        cv_parts.extend(["", "Personal Projects:", "\n".join(personal_project_lines)])

    if publications_lines:
        cv_parts.extend(["", "Publications:", "\n".join(publications_lines)])

    return "\n".join(cv_parts)


def _build_technical_review_prompt(cv_data: dict[str, object], job_description: str) -> str:
    cv_text = _format_cv_data_for_prompt(cv_data)

    return f"""**Your Role**: Senior Technical Lead reviewing a candidate's tailored CV for a specific technical position.

**Evaluation Criteria** (assess each):
1. **Technical Depth** — Do the highlights demonstrate real technical understanding or just buzzword listing? Look for: specific technologies with context, architectural decisions, scale indicators (users, requests/sec, data volume)
2. **Stack Relevance** — How well do the candidate's technologies match the JD requirements? Identify exact matches, transferable skills, and critical gaps
3. **Project Credibility** — Are project descriptions believable and specific? Vague claims like "improved performance" without metrics are red flags. Look for STAR-format evidence (Situation, Task, Action, Result)
4. **Skill Progression** — Does the candidate show growth? Are they using modern tools/frameworks or stuck on legacy tech? Is the progression from junior to senior roles reflected in increasing responsibility?
5. **Technical Achievements** — Are quantified metrics present and realistic? "Reduced latency by 99%" is suspicious. "Reduced P95 latency from 800ms to 200ms" is credible
6. **Missing Technical Skills** — Key technical requirements from the JD that the candidate lacks (but DO NOT recommend adding skills not present in the source documents — only note the gap)

**Scoring Guide**:
- 9-10: Technically exceptional, deep expertise matching JD requirements
- 7-8: Strong technical profile, minor skill gaps
- 5-6: Adequate technical background, notable gaps in key areas
- 3-4: Weak technical fit, fundamental skill mismatches
- 1-2: Technical profile does not match role requirements

**Set reviewer_role to "technical" in your output.**

**CRITICAL**: Do NOT recommend adding technologies or skills not present in the CV. You can only suggest better phrasing, reordering, emphasis changes, or removing weak content.

**Candidate CV Data**:
{cv_text}

---
**Job Description**:
{job_description}
---
"""


async def review_as_technical(
    cv_data: dict[str, object],
    job_description: str,
    model_name: str,
    api_key: str,
) -> ReviewMemo:
    model = create_model_from_string(model_name, api_key)
    prompt = _build_technical_review_prompt(cv_data, job_description)
    result = await technical_reviewer_agent.run(prompt, model=model)
    return result.output
