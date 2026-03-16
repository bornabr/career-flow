"""Post-generation CV validation: ATS cleaning, hallucination detection, null section removal.

Heuristic (non-AI) validation pipeline. Checks skills, experience highlights,
and summary claims against the original resume text using fuzzy matching and
synonym awareness.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

from app.utils.ats import ats_clean_data

# ---------------------------------------------------------------------------
# Synonym / alias map — common equivalent terms that should not be flagged
# ---------------------------------------------------------------------------
_SKILL_SYNONYMS: dict[str, set[str]] = {
    "javascript": {"js", "ecmascript", "es6", "es2015"},
    "typescript": {"ts"},
    "python": {"py", "python3", "cpython"},
    "react": {"reactjs", "react.js"},
    "vue": {"vuejs", "vue.js"},
    "angular": {"angularjs", "angular.js"},
    "node": {"nodejs", "node.js"},
    "next": {"nextjs", "next.js"},
    "nuxt": {"nuxtjs", "nuxt.js"},
    "postgres": {"postgresql", "psql"},
    "mongo": {"mongodb"},
    "redis": {"redis-server"},
    "docker": {"containerization", "containers"},
    "kubernetes": {"k8s"},
    "aws": {"amazon web services"},
    "gcp": {"google cloud", "google cloud platform"},
    "azure": {"microsoft azure"},
    "ci/cd": {"cicd", "ci cd", "continuous integration", "continuous deployment"},
    "ml": {"machine learning"},
    "ai": {"artificial intelligence"},
    "nlp": {"natural language processing"},
    "css": {"css3", "cascading style sheets"},
    "html": {"html5"},
    "sql": {"structured query language"},
    "nosql": {"no-sql"},
    "rest": {"restful", "rest api", "restful api"},
    "graphql": {"gql"},
    "terraform": {"tf"},
    "c++": {"cpp"},
    "c#": {"csharp", "c sharp"},
    "go": {"golang"},
    "rust": {"rustlang"},
    "java": {"jvm"},
    "swift": {"swiftui"},
    "api": {"apis", "web api", "web apis"},
    "microservices": {"micro-services", "micro services"},
    "devops": {"dev-ops", "dev ops"},
    "agile": {"scrum", "kanban"},
    "ui": {"user interface"},
    "ux": {"user experience"},
    "ui/ux": {"ui ux", "ux/ui"},
}

# Build reverse lookup: synonym → canonical
_SYNONYM_REVERSE: dict[str, str] = {}
for _canonical, _synonyms in _SKILL_SYNONYMS.items():
    for _syn in _synonyms:
        _SYNONYM_REVERSE[_syn] = _canonical
    _SYNONYM_REVERSE[_canonical] = _canonical


def _normalize(text: str) -> str:
    """Lowercase, strip, collapse whitespace."""
    return " ".join(text.lower().split())


def _fuzzy_match(needle: str, haystack: str, threshold: float = 0.80) -> bool:
    """Check if needle appears in haystack using fuzzy substring matching.

    Uses SequenceMatcher ratio on sliding windows of the haystack to find
    the best local match. Returns True if the best ratio >= threshold.
    """
    needle_norm = _normalize(needle)
    haystack_norm = _normalize(haystack)

    if not needle_norm:
        return True

    # Exact substring check first (fast path)
    if needle_norm in haystack_norm:
        return True

    # Check synonym equivalence
    canonical = _SYNONYM_REVERSE.get(needle_norm)
    if canonical:
        # Check if canonical or any synonym appears in haystack
        all_variants = {canonical} | _SKILL_SYNONYMS.get(canonical, set())
        for variant in all_variants:
            if variant in haystack_norm:
                return True

    # Fuzzy sliding-window check for short terms (< 5 words)
    needle_words = needle_norm.split()
    if len(needle_words) > 5:
        # For long phrases, just check overall ratio
        return SequenceMatcher(None, needle_norm, haystack_norm).ratio() >= threshold

    # Slide a window of similar length across the haystack
    haystack_words = haystack_norm.split()
    window_size = len(needle_words)
    best_ratio = 0.0
    for i in range(len(haystack_words) - window_size + 1):
        window = " ".join(haystack_words[i : i + window_size])
        ratio = SequenceMatcher(None, needle_norm, window).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            if best_ratio >= threshold:
                return True

    return best_ratio >= threshold


def check_hallucinations(cv_data: dict[str, Any], original_resume: str) -> list[str]:
    """Compare generated CV against original resume to detect hallucinated content.

    Checks:
    1. Skills entries — each skill detail checked against resume
    2. Experience highlights — key claims checked against resume
    3. Summary claims — checked against resume
    4. Company names and positions — exact match expected

    Uses fuzzy matching and synonym awareness to reduce false positives.
    Returns a list of potentially hallucinated items for user review.
    """
    hallucinated: list[str] = []
    sections = cv_data.get("sections", {})

    # --- Skills check ---
    skills = sections.get("Skills", [])
    for entry in skills:
        label = entry.get("label", "")
        details = entry.get("details", "")
        for detail in details.split(","):
            detail_stripped = detail.strip()
            if not detail_stripped:
                continue
            # Check both the individual skill and label+skill combo
            if not _fuzzy_match(detail_stripped, original_resume) and not _fuzzy_match(
                label, original_resume
            ):
                hallucinated.append(f"Skill: {label} — {detail_stripped}")

    # --- Experience company/position check ---
    for section_key in ("Experience", "AdditionalExperience"):
        for exp in sections.get(section_key, []) or []:
            company = exp.get("company", "")
            position = exp.get("position", "")

            if company and not _fuzzy_match(company, original_resume, threshold=0.85):
                hallucinated.append(f"Company not found: {company}")

            if position and not _fuzzy_match(position, original_resume, threshold=0.80):
                hallucinated.append(f"Position not found: {position}")

            # Check highlights for numeric claims
            for highlight in exp.get("highlights", []):
                _check_numeric_claims(highlight, original_resume, hallucinated)

    # --- Summary check for strong claims ---
    summary_parts = sections.get("Summary", [])
    for part in summary_parts:
        _check_numeric_claims(part, original_resume, hallucinated)

    return hallucinated


def _check_numeric_claims(text: str, resume: str, hallucinated: list[str]) -> None:

    # Match patterns like: 40%, $2M, 100K users, 15+ years, 3x, 200ms
    numeric_patterns = re.findall(
        r"""
        \$[\d,.]+[KMBkmb]?         |  # Dollar amounts
        \d+(?:\.\d+)?%             |  # Percentages
        \d+(?:\.\d+)?[KMBkmb]\b   |  # Abbreviated numbers (10K, 2M)
        \d+(?:\.\d+)?x\b          |  # Multipliers (3x, 10x)
        \d+\+?\s*(?:years?|yrs?)     # Year counts
        """,
        text,
        re.VERBOSE | re.IGNORECASE,
    )

    for claim in numeric_patterns:
        claim_stripped = claim.strip()
        if claim_stripped and not _fuzzy_match(claim_stripped, resume, threshold=0.90):
            hallucinated.append(f"Numeric claim not in resume: '{claim_stripped}' in '{text[:80]}'")


def validate_cv(cv_data: dict[str, Any], original_resume: str) -> dict[str, Any]:
    """Run validation pipeline on generated CV data.

    1. ATS-clean all text (non-ASCII → ASCII, flag issues)
    2. Detect potential hallucinations (fuzzy + synonym-aware)
    3. Remove empty/null sections

    Returns dict with 'cv_data', 'ats_issues', and 'hallucination_warnings'.
    """
    cleaned_result, ats_issues = ats_clean_data(cv_data)
    cleaned_data = cleaned_result if isinstance(cleaned_result, dict) else cv_data

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
