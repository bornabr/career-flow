import re
import unicodedata

# Common non-ASCII to ASCII replacements for ATS compatibility
_ATS_REPLACEMENTS: dict[str, str] = {
    "\u201c": '"', "\u201d": '"', "\u2018": "'", "\u2019": "'",
    "\u2013": "-", "\u2014": "-", "\u2212": "-", "\u2022": "-",
    "\u2026": "...", "\u00b4": "'",
    "\u2192": "->", "\u2190": "<-", "\u21d2": "=>", "\u2260": "!=",
    "\u00ae": "", "\u00a9": "", "\u2122": "",
    "\u00a0": " ",
}


def ats_friendly_text(text: str) -> tuple[str, list[str]]:
    """Replace non-ASCII characters with ASCII equivalents and flag problematic ones.

    Returns (cleaned_text, issues_list).
    """
    issues: list[str] = []

    def replace_char(c: str) -> str:
        if c in _ATS_REPLACEMENTS:
            return _ATS_REPLACEMENTS[c]
        if ord(c) > 127:
            normalized = unicodedata.normalize("NFKD", c)
            if all(ord(x) < 128 for x in normalized):
                return normalized
            issues.append(f"Non-ASCII character: '{c}' (U+{ord(c):04X})")
            return ""
        return c

    cleaned = "".join(replace_char(c) for c in text)

    if re.search(r"[\u2022\u25cf\u25a0]", text):
        issues.append("Bullet symbols detected. Use '-' or '*' instead.")
    if re.search(r"[\u00a0]", text):
        issues.append("Non-breaking spaces detected. Use regular spaces.")
    if re.search(r"\|", text):
        issues.append("Vertical bars '|' detected. Avoid tables for ATS.")

    return cleaned, issues


def ats_clean_data(data: object) -> tuple[object, list[str]]:
    """Recursively clean all string values in a dict/list for ATS-friendliness."""
    issues: list[str] = []

    def _clean(val: object) -> object:
        if isinstance(val, str):
            cleaned, found = ats_friendly_text(val)
            issues.extend(found)
            return cleaned
        elif isinstance(val, list):
            return [_clean(v) for v in val]
        elif isinstance(val, dict):
            return {k: _clean(v) for k, v in val.items()}
        return val

    cleaned_data = _clean(data)
    return cleaned_data, list(set(issues))


def validate_date(date_str: str) -> bool:
    """Check if a date string matches YYYY-MM, YYYY, or 'present'."""
    if not date_str:
        return True
    if date_str.lower() == "present":
        return True
    if re.match(r"^\d{4}-\d{2}$", date_str):
        return True
    if re.match(r"^\d{4}$", date_str):
        return True
    return False
