from pydantic_ai import Agent

from app.schemas.cv import CV
from app.schemas.review import ReviewMemo
from app.services.llm import create_model_from_string

SYNTHESIS_SYSTEM_PROMPT = (
    "You are an expert CV refinement editor. Refine an existing tailored CV using review panel feedback from HR, "
    "Technical, and ATS reviewers. You are NOT generating from scratch. All three reviewer perspectives have equal "
    "weight. If reviewer guidance conflicts, prioritize factual accuracy to source documents. "
    "CRITICAL ANTI-HALLUCINATION RULE: never add, infer, or fabricate details not explicitly supported by the "
    "original resume text and existing CV draft. Do not invent skills, experiences, metrics, job titles, education, "
    "publications, projects, or credentials. You may only reorganize, rephrase, reorder, or de-emphasize existing "
    "content. Use the job description only to prioritize and frame existing facts. Maintain strict CV schema "
    "compliance and keep output concise enough for a single-page resume."
)


synthesis_agent = Agent(
    "test",
    output_type=CV,
    system_prompt=SYNTHESIS_SYSTEM_PROMPT,
)


def _format_review_memos(reviews: list[ReviewMemo]) -> str:
    if not reviews:
        return "No review memos provided."

    review_blocks: list[str] = []
    for index, review in enumerate(reviews, start=1):
        item_lines = [
            (
                f"  - category: {item.category}\n"
                f"    severity: {item.severity}\n"
                f"    section: {item.section}\n"
                f"    finding: {item.finding}\n"
                f"    recommendation: {item.recommendation}"
            )
            for item in review.items
        ]

        strengths = [f"  - {strength}" for strength in review.strengths] or ["  - None"]
        weaknesses = [f"  - {weakness}" for weakness in review.weaknesses] or ["  - None"]
        priority_changes = [f"  - {change}" for change in review.priority_changes] or ["  - None"]

        review_blocks.append(
            "\n".join(
                [
                    f"Reviewer {index}: {review.reviewer_role}",
                    f"Overall score: {review.overall_score}/10",
                    "Strengths:",
                    *strengths,
                    "Weaknesses:",
                    *weaknesses,
                    "Priority changes:",
                    *priority_changes,
                    "Detailed findings:",
                    *(item_lines or ["  - None"]),
                ]
            )
        )

    return "\n\n".join(review_blocks)


def _format_scalar(value: object) -> str:
    if value is None:
        return "(none)"
    return str(value)


def _format_nested_value(value: object, indent: int) -> list[str]:
    prefix = " " * indent

    if isinstance(value, dict):
        if not value:
            return [f"{prefix}(none)"]
        mapping_lines: list[str] = []
        for key, nested_value in value.items():
            mapping_lines.append(f"{prefix}{key}:")
            mapping_lines.extend(_format_nested_value(nested_value, indent + 2))
        return mapping_lines

    if isinstance(value, list):
        if not value:
            return [f"{prefix}- (none)"]
        lines: list[str] = []
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}-")
                lines.extend(_format_nested_value(item, indent + 2))
            else:
                lines.append(f"{prefix}- {_format_scalar(item)}")
        return lines

    return [f"{prefix}{_format_scalar(value)}"]


def _format_cv_data_for_prompt(cv_data: dict[str, object]) -> str:
    sections_raw = cv_data.get("sections", {})
    sections = sections_raw if isinstance(sections_raw, dict) else {}

    formatted_cv = {
        "name": cv_data.get("name"),
        "location": cv_data.get("location"),
        "email": cv_data.get("email"),
        "phone": cv_data.get("phone"),
        "website": cv_data.get("website"),
        "social_networks": cv_data.get("social_networks") or [],
        "sections": {
            "Summary": sections.get("Summary") or [],
            "Experience": sections.get("Experience") or [],
            "AdditionalExperience": sections.get("AdditionalExperience") or [],
            "Skills": sections.get("Skills") or [],
            "Education": sections.get("Education") or [],
            "Publications": sections.get("Publications") or [],
            "PersonalProjects": sections.get("PersonalProjects") or [],
        },
    }

    lines: list[str] = []
    for key, value in formatted_cv.items():
        lines.append(f"{key}:")
        lines.extend(_format_nested_value(value, indent=2))
    return "\n".join(lines)


def _build_synthesis_prompt(
    cv_data: dict[str, object],
    reviews: list[ReviewMemo],
    resume_text: str,
    job_description: str,
) -> str:
    cv_text = _format_cv_data_for_prompt(cv_data)
    review_text = _format_review_memos(reviews)

    return f"""You are refining an existing tailored CV based on three reviewer memos.

Instructions:
1. Refine the current CV draft; do not generate a brand-new CV.
2. Treat HR, Technical, and ATS reviewer recommendations with equal weight.
3. Incorporate reviewer recommendations where they improve quality and relevance.
4. When recommendations conflict, choose the option most truthful to the original resume text and current CV draft.
5. Never add facts from the job description; use it only to prioritize framing and ordering.
6. Maintain full CV schema compliance.
7. Keep output concise to preserve a single-page target.

Current CV Draft (structured):
{cv_text}

---
Reviewer Memos (scores, findings, priority changes):
{review_text}

---
Original Resume Text (ground truth for anti-hallucination):
{resume_text}

---
Job Description (target context only):
{job_description}
"""


async def synthesize_cv(
    cv_data: dict[str, object],
    reviews: list[ReviewMemo],
    resume_text: str,
    job_description: str,
    model_name: str,
    api_key: str,
) -> CV:
    model = create_model_from_string(model_name, api_key)
    prompt = _build_synthesis_prompt(cv_data, reviews, resume_text, job_description)
    result = await synthesis_agent.run(prompt, model=model)
    return result.output
