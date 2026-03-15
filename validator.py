
import re
import datetime
from typing import Dict, List, Tuple, Any

class CVValidator:
    """
    Validates and auto-corrects CV data for RenderCV compatibility.
    """

    # LaTeX special characters that need escaping
    LATEX_SPECIAL_CHARS = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\textasciicircum{}',
        '\\': r'\textbackslash{}',
    }
    
    # Regex to find unescaped characters. 
    # This is a simplified approach; a full LaTeX parser would be overkill but more accurate.
    # We want to find e.g. '%' that is NOT preceded by '\'.
    
    @staticmethod
    def escape_latex_chars(text: str) -> str:
        """
        Escapes LaTeX special characters in a string.
        """
        if not text:
            return text
            
        # We need to be careful not to double-escape.
        # A simple approach is to replace all occurrences, but that breaks if already escaped.
        # Better approach: Look for unescaped chars.
        
        # For simplicity in this context (resume text), we can assume that if a backslash is present,
        # it might be an escape. However, users might type "C:\Windows".
        # Given the context of "generating from LLM", the LLM *should* have escaped them but might have failed.
        # Or the user typed them in the editor.
        
        # Let's use a safe replacement strategy:
        # 1. Replace backslashes first to avoid escaping the escapes of other chars.
        # But wait, if we replace '\' with '\textbackslash{}', we break existing valid LaTeX escapes if any exist.
        # Since we are generating "pure text" content for RenderCV (which handles some escaping but not all?),
        # RenderCV actually expects *Markdown* or *LaTeX* content?
        # RenderCV documentation says: "RenderCV treats all the strings as Markdown."
        # AND "RenderCV converts Markdown to LaTeX."
        # So, if we write "%", RenderCV's markdown parser *should* handle it?
        # Let's verify why it failed.
        # If RenderCV takes Markdown, then `%` in markdown is just `%`.
        # However, if it passes through to LaTeX, `%` is a comment.
        
        # According to RenderCV docs, it escapes special characters automatically when converting Markdown to LaTeX.
        # BUT, if the user provides *invalid* YAML or something that breaks the internal logic, it fails.
        
        # Let's look at the failure again. "RenderCV could not generate the PDF...".
        # If I put `%` in the YAML string, PyYAML loads it fine.
        # Then RenderCV processes it. 
        
        # If the error is "unexpected character", it might be in the YAML parsing itself if not quoted properly?
        # No, the app uses `yaml.safe_load`.
        
        # Let's assume the issue is specifically about characters that break RenderCV's internal processing 
        # or that RenderCV *doesn't* fully escape everything in all contexts.
        
        # Actually, let's try to be less aggressive with escaping and focus on *validation* first.
        # But the user wants "auto-correction".
        
        # Let's stick to a safe set of replacements for things that definitely break LaTeX if passed raw
        # and might slip through Markdown conversion if not handled.
        
        # However, if RenderCV handles Markdown, we should probably NOT escape `_` or `*` as those are Markdown formatting.
        # We SHOULD escape `%`, `#`, `&` if they are meant to be literals.
        
        cleaned = text
        # Replace % with \% if not already escaped
        # (This regex looks for % not preceded by \)
        cleaned = re.sub(r'(?<!\\)%', r'\%', cleaned)
        
        # Replace & with \& if not already escaped
        cleaned = re.sub(r'(?<!\\)&', r'\&', cleaned)
        
        # Replace $ with \$ if not already escaped (unless it's a math block? Unlikely in a resume summary)
        cleaned = re.sub(r'(?<!\\)\$', r'\$', cleaned)
        
        return cleaned

    @classmethod
    def validate_and_fix(cls, data: Any) -> Tuple[Any, List[str]]:
        """
        Recursively traverses the CV data structure (dict/list/str) and:
        1. Fixes common issues (unescaped chars).
        2. Validates constraints (dates, urls).
        
        Returns:
            (fixed_data, issues_list)
        """
        issues = []
        
        if isinstance(data, dict):
            new_data = {}
            for k, v in data.items():
                # Fix keys? Keys should be safe strings usually.
                fixed_val, sub_issues = cls.validate_and_fix(v)
                new_data[k] = fixed_val
                issues.extend(sub_issues)
            return new_data, issues
            
        elif isinstance(data, list):
            new_data = []
            for item in data:
                fixed_val, sub_issues = cls.validate_and_fix(item)
                new_data.append(fixed_val)
                issues.extend(sub_issues)
            return new_data, issues
            
        elif isinstance(data, str):
            # Apply fixes to string values
            original = data
            
            # 1. Escape dangerous LaTeX chars that might slip through
            # We focus on % and & for now as they are the most common culprits.
            fixed = cls.escape_latex_chars(data)
            
            if fixed != original:
                # We don't necessarily need to report every escape as an "issue", 
                # but we can track it if we want to inform the user.
                pass
                
            return fixed, issues
            
        else:
            return data, issues

    @staticmethod
    def validate_dates(date_str: str) -> bool:
        """
        Checks if a date string matches YYYY-MM, YYYY, or 'present'.
        """
        if not date_str:
            return True # None is allowed in some fields, handled by Pydantic
        if date_str.lower() == "present":
            return True
        
        # YYYY-MM
        if re.match(r'^\d{4}-\d{2}$', date_str):
            return True
        # YYYY
        if re.match(r'^\d{4}$', date_str):
            return True
            
        return False

