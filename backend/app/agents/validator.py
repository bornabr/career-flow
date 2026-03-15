from app.schemas.cv import CV
from app.utils.ats import ats_clean_data


def check_hallucinations(cv_data: dict, original_resume: str) -> list[str]:
    """Compare generated CV against original resume to detect hallucinated content.

    Checks skills entries against the original resume text. Returns a list of
    potentially hallucinated items for user review.
    """
    resume_lower = original_resume.lower()
    hallucinated: list[str] = []

    skills = cv_data.get("sections", {}).get("Skills", [])
    for entry in skills:
        label = entry.get("label", "")
        details = entry.get("details", "")
        for detail in details.split(","):
            detail_stripped = detail.strip().lower()
            if detail_stripped and detail_stripped not in resume_lower and label.lower() not in resume_lower:
                hallucinated.append(f"{label} - {detail.strip()}")

    return hallucinated


def validate_cv(cv_data: dict, original_resume: str) -> dict:
    """Run validation pipeline on generated CV data.

    1. ATS-clean all text (non-ASCII → ASCII, flag issues)
    2. Detect potential hallucinations
    3. Remove empty/null sections

    Returns dict with 'cv_data', 'ats_issues', and 'hallucination_warnings'.
    """
    cleaned_data, ats_issues = ats_clean_data(cv_data)

    hallucination_warnings = check_hallucinations(cleaned_data, original_resume)

    # Remove null sections
    if isinstance(cleaned_data, dict) and "sections" in cleaned_data:
        cleaned_data["sections"] = {
            k: v for k, v in cleaned_data["sections"].items() if v is not None
        }

    return {
        "cv_data": cleaned_data,
        "ats_issues": ats_issues,
        "hallucination_warnings": hallucination_warnings,
    }
