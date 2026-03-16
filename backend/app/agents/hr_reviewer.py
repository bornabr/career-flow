from pydantic_ai import Agent

from app.schemas.review import ReviewMemo
from app.services.llm import create_model_from_string

HR_REVIEWER_SYSTEM_PROMPT = (
    "You are a Senior HR Director with 15+ years of experience in talent acquisition and candidate screening. "
    "You evaluate resumes from a recruiter's perspective, focusing on candidate-job fit, career progression, "
    "red flags, and presentation quality. You return structured JSON feedback according to the provided schema. "
    "You must NEVER hallucinate - only reference content present in the CV and job description."
)


hr_reviewer_agent = Agent(
    "test",
    output_type=ReviewMemo,
    system_prompt=HR_REVIEWER_SYSTEM_PROMPT,
)


def _format_cv_for_prompt(cv_data: dict) -> str:
    name = cv_data.get("name", "the candidate")
    sections = cv_data.get("sections", {})

    summary = " ".join(sections.get("Summary", []))

    experience_lines = []
    for exp in sections.get("Experience", []):
        role = f"{exp.get('position', '')} at {exp.get('company', '')}".strip()
        period_parts = [exp.get("start_date", ""), exp.get("end_date", "")]
        period = " - ".join([p for p in period_parts if p])
        highlights = "; ".join(exp.get("highlights", []))

        line = f"- {role}" if role else "-"
        if period:
            line = f"{line} ({period})"
        if highlights:
            line = f"{line}: {highlights}"
        experience_lines.append(line)

    skills_lines = []
    for skill in sections.get("Skills", []):
        label = skill.get("label", "")
        details = skill.get("details", "")
        skills_lines.append(f"- {label}: {details}".rstrip(": "))

    education_lines = []
    for edu in sections.get("Education", []):
        degree = edu.get("degree", "")
        institution = edu.get("institution", "")
        end_date = edu.get("end_date", "")
        edu_line = f"- {degree} at {institution}".strip()
        if end_date:
            edu_line = f"{edu_line} ({end_date})"
        education_lines.append(edu_line)

    experience_text = "\n".join(experience_lines) if experience_lines else "-"
    skills_text = "\n".join(skills_lines) if skills_lines else "-"
    education_text = "\n".join(education_lines) if education_lines else "-"

    return f"""Name: {name}
Summary: {summary}

Experience:
{experience_text}

Skills:
{skills_text}

Education:
{education_text}"""


def _build_hr_review_prompt(cv_data: dict, job_description: str) -> str:
    cv_text = _format_cv_for_prompt(cv_data)

    return f"""**Your Role**: Senior HR Director reviewing a candidate's tailored CV for a specific position.

**Evaluation Criteria** (assess each):
1. **Career Progression** - Is the career trajectory logical? Any unexplained gaps > 6 months? Job-hopping patterns (3+ roles < 1 year)?
2. **Role-JD Alignment** - Does the candidate's experience level match the job requirements? Over-qualified or under-qualified signals?
3. **Cultural Fit Signals** - Does the language suggest team orientation vs. solo work? Leadership vs. individual contributor alignment with the role?
4. **Presentation Quality** - Is the summary compelling? Are highlights concise and impactful? Is the overall length appropriate (~1 page)?
5. **Red Flags** - Vague descriptions without specifics, buzzword stuffing without substance, inconsistent dates, title inflation
6. **Missing Information** - Key qualifications from the JD that are absent from the CV (but DO NOT recommend adding info not in the source documents)

**Scoring Guide**:
- 9-10: Excellent match, would immediately schedule interview
- 7-8: Strong candidate, minor improvements needed
- 5-6: Moderate match, significant gaps to address
- 3-4: Weak match, major concerns
- 1-2: Poor fit for this role

**Set reviewer_role to "hr" in your output.**

**CRITICAL**: Do NOT recommend adding information that isn't present in the CV. You can only suggest restructuring, reordering, rephrasing, or removing existing content.

**Candidate CV Data**:
{cv_text}

---
**Job Description**:
{job_description}
---
"""


async def review_as_hr(cv_data: dict, job_description: str, model_name: str, api_key: str) -> ReviewMemo:
    model = create_model_from_string(model_name, api_key)
    prompt = _build_hr_review_prompt(cv_data, job_description)
    result = await hr_reviewer_agent.run(prompt, model=model)
    return result.output
