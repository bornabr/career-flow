import streamlit as st
import fitz  # PyMuPDF
import io
import json
from pydantic import BaseModel, Field, ValidationError, HttpUrl
from typing import List, Optional
import datetime
import subprocess
import yaml
import uuid
from rendercv.cli.commands import cli_command_render
import base64
from code_editor import code_editor
from streamlit_local_storage import LocalStorage
from streamlit_pdf_viewer import pdf_viewer
import contextlib
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.providers.google import GoogleProvider

# Recursively clean all string values in a dict/list for ATS-friendliness
def ats_clean_data(data):
    issues = []
    def _clean(val):
        if isinstance(val, str):
            cleaned, found = ats_friendly_text(val)
            issues.extend(found)
            return cleaned
        elif isinstance(val, list):
            return [_clean(v) for v in val]
        elif isinstance(val, dict):
            return {k: _clean(v) for k, v in val.items()}
        elif isinstance(val, HttpUrl):
            return str(val)
        else:
            return val
    cleaned_data = _clean(data)
    return cleaned_data, list(set(issues))
# --- ATS Friendliness Audit ---
import unicodedata
import re
import os
from dotenv import load_dotenv
load_dotenv()
MODEL_NAME = os.environ.get("MODEL_NAME", "openai:gpt-4o")
PROVIDER = MODEL_NAME.split(":")[0] if ":" in MODEL_NAME else "openai"
print(f"Using {PROVIDER} model: {MODEL_NAME}")

# Pydantic Models for RenderCV Structure
# These models define the exact structure RenderCV expects.

MOCK_TEST = False  # Set to True for development/testing with mock data

def ats_friendly_text(text: str):
    """
    Replace non-ASCII characters with ASCII equivalents and flag problematic ones for ATS friendliness.
    Returns (cleaned_text, issues_list)
    """
    # Map of common non-ASCII to ASCII replacements
    replacements = {
        '“': '"', '”': '"', '‘': "'", '’': "'",
        '–': '-', '—': '-', '−': '-', '•': '-',
        '…': '...', '´': "'", '•': '-',
        '→': '->', '←': '<-', '⇒': '=>', '≠': '!=',
        '®': '', '©': '', '™': '',
        '\u00a0': ' ', # non-breaking space
    }
    issues = []
    def replace_char(c):
        if c in replacements:
            return replacements[c]
        if ord(c) > 127:
            # Try to normalize, else flag
            normalized = unicodedata.normalize('NFKD', c)
            if all(ord(x) < 128 for x in normalized):
                return normalized
            issues.append(f"Non-ASCII character: '{c}' (U+{ord(c):04X})")
            return ''
        return c
    cleaned = ''.join(replace_char(c) for c in text)
    # Flag other ATS-unfriendly patterns
    if re.search(r'[\u2022\u25CF\u25A0]', text):
        issues.append("Bullet symbols detected. Use '-' or '*' instead.")
    if re.search(r'[\u00A0]', text):
        issues.append("Non-breaking spaces detected. Use regular spaces.")
    # Warn about tables or images (very basic check)
    if re.search(r'\|', text):
        issues.append("Vertical bars '|' detected. Avoid tables for ATS.")
    return cleaned, issues

class SocialNetwork(BaseModel):
    network: str
    username: str = Field(..., description="Username for the social network (do not add the whole URL)")

class CV(BaseModel):
    name: str
    location: str
    email: Optional[str] = None
    phone: Optional[str] = Field(
        ..., 
        pattern=r"^\+?[1-9]\d{1,14}$",
        description="Phone number in E.164 format (e.g., +15555555555)"
    )
    website: Optional[HttpUrl] = None
    social_networks: Optional[List[SocialNetwork]] = None
    sections: 'Sections'

class ExperienceEntry(BaseModel):
    company: str
    position: str
    location: Optional[str] = None
    start_date: Optional[str] = Field(default=None, description="Start date in YYYY-MM format")
    end_date: Optional[str] = Field(default=None, description="End date in YYYY-MM or 'present' format")
    highlights: List[str] = Field(..., description="List of action-oriented highlights for the role. Quantify achievements where possible. Tailor these to the job description.")
    summary: Optional[str] = Field(default=None, description="A brief summary of the role. Tailor this to the job description. Don't include if not applicable.")   

class EducationEntry(BaseModel):
    institution: str
    area: str
    degree: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[str] = Field(default=None, description="Start date in YYYY-MM format")
    end_date: Optional[str] = Field(default=None, description="End date in YYYY-MM format")
    highlights: Optional[List[str]] = Field(default=None, description="List of highlights or relevant coursework. Tailor these to the job description. Don't include if not applicable.")
    summary: Optional[str] = Field(default=None, description="A brief summary of the education entry. Tailor this to the job description. Don't include if not applicable.")


class OneLineEntry(BaseModel):
    label: str
    details: str

# Personal Project Entry Model
class PersonalProjectEntry(BaseModel):
    name: str
    summary: str = Field(..., description="Brief description of the project, including technologies used and impact.")
    highlights: Optional[List[str]] = Field(default=None, description="Key achievements or features. Tailor these to the job description.")
    url: Optional[HttpUrl] = Field(default=None, description="URL to the project or repository. Omit if not applicable.")

class PublicationsEntry(BaseModel):
    title: str
    authors: List[str]
    doi: Optional[str] = None
    journal: str
    date: Optional[str] = Field(default=None, description="Publication date in YYYY format")
    url: HttpUrl
    

class Sections(BaseModel):
    Summary: List[str] = Field(..., description="A 2-3 sentence professional summary, tailored to the job description, split into a list of strings.")
    Skills: List[OneLineEntry]
    Education: List[EducationEntry]
    Experience: List[ExperienceEntry]
    AdditionalExperience: Optional[List[ExperienceEntry]] = Field(default=None, description="Additional experience entries that may not fit to the job description in case the user wants to include them.")
    Publications: Optional[List[PublicationsEntry]] = Field(default=None, description="List of publications. Optional; omit if not applicable.")
    PersonalProjects: Optional[List[PersonalProjectEntry]] = Field(default=None, description="List of personal projects relevant to the job. Each entry should highlight technologies, impact, and relevance.")

# This is required for Pydantic v1/v2 compatibility for forward references.
CV.model_rebuild()
Sections.model_rebuild()

def _build_prompt(resume: str, job_desc: str, user_prompt: Optional[str] = None) -> str:
    """Construct the system/user prompt with strict instructions.

    The prompt enforces:
    - Schema compliance
    - No hallucination
    - Irrelevant content filtering
    - Highlight merging/splitting guidelines
    """

    user_section = ""
    if user_prompt:
        user_section = f"**Additional User Instructions:**\n{user_prompt}\n\n"

    return f"""
**Role**: You are a world-class professional resume writer and career-coach AI. Your mission is to transform a generic resume into a highly-tailored, compelling CV optimized for a specific job description.

**CRITICAL RULE: NO HALLUCINATION**
You must NEVER invent, infer, or add any information that is not explicitly present in the resume. If a detail is not present in the resume, you must omit it, even if it appears in the job description. Do not guess, synthesize, or fill in gaps from the job description. Only bold or emphasize keywords from the job description if they are present in the resume content.

**Objective**: Produce **one** JSON object that conforms **exactly** to the provided Pydantic and rendercv (v2) schema.

---
**Non-Negotiable Constraints**
1. **NO HALLUCINATION** - Only include details that are explicitly present in the resume. If a field is missing, leave it out. Do not add, infer, or guess any information from the job description.
2. **Schema Fidelity** - Output **must** be valid JSON matching the `CV` model (no extra keys).
3. **Relevancy Filter** - Include *only* experience, skills, education, and personal projects that directly or indirectly support the job description, but only if they are present in the resume. Drop the rest.
4. **Additional Experience** - Rewrite and include all experience entries that did not fit the job description and were not included in the experience section. User may add these entries explicitly if they want to include them.
5. **Highlights Hygiene** -
   - Split overly long or compound highlights into concise bullets (≤2 lines each).
   - Each Experience can have up to 4 highlights for recent roles and 3 for older roles.
   - Each Personal Project can have up to 3 highlights, focused on technologies, impact, and relevance to the job.
6. **Action Verbs & Metrics** - Start bullets with strong verbs (e.g., "Led", "Architected") and quantify impact when possible (e.g., "Increased efficiency by 30%," "Managed a team of 5") but don't hallucinate quantification.
7. **Markdown Emphasis** - Bold (`**`) any keyword that *exactly* matches a skill or responsibility from the job description (in `highlights`, `summary`, and `personal projects`), but only if that keyword is present in the resume.
8. **Date Format** - Use YYYY-MM, YYYY, or "present" exactly as defined in the schema.
9. **Username Extraction** - Return only usernames for social links (e.g., GitHub, LinkedIn).
10. **Single-Page Target** - Keep the final CV to about **one page** (≈500-600 words when rendered). Trim or omit less critical details to fit including old experiences, non-relevant skills, and other extraneous information.
11. **Publications** - Must include this section if it is present in the resume. It follow the same rules as Experience and Education regarding highlights and relevance.
12. **Personal Projects** - Must include this section if it is present in the resume. It follow the same rules as Experience and Education regarding highlights and relevance.

---
**Step-by-Step Process (internal - do not output)**
1. **Analyse Inputs** - Identify the 5-7 most critical keywords/skills from the Job Description that are strongly relevant to the user's background. Map resume content to those, but do NOT add any new content from the job description unless it is present in the resume.
2. **Synthesise Content** -
   - **Summary** - 2-3 sentences (≤3 lines totally) that pitch the candidate using only those keywords that are present in the resume.
   - **Experience** - Rewrite recent roles and their highlights; rewrite or remove older ones based on relevance. Ensure highlights follow Constraint 4 and overall length supports the single-page goal. Do not add any new experience or skills from the job description.
   - **Skills** - Present only relevant skills, grouped under clear labels. Do not add missing JD keywords unless they are present in the resume.
   - **Education** - Generally does not need any highlights. Only include entries when they directly strengthen candidacy for the role and are present in the resume.
   - **Publications** - Include publications to showcase expertise, but only if present in the resume. Publications is an optional section, so if no relevant publications exist, this section can be omitted. For author names (if present), write every author name in the format "First letter of first name. Last name" (e.g., "J. Smith") except for the resume owner's name which should be written in full.
   - **Personal Projects** - Include personal projects that demonstrate relevant skills, technologies, or impact, but only if present in the resume. Personal projects is an optional section, so if no relevant projects exist, this section can be omitted.
3. **Assemble JSON** - Populate the `CV` object and return *only* the JSON.

---
{user_section}**Resume Content**:
{resume}

---
**Job Description**:
{job_desc}
---
"""

def get_model_instance(api_key: str):
    """Create a PydanticAI model instance based on the configured provider."""
    model_name = MODEL_NAME.split(":")[-1]

    if PROVIDER == "openai":
        provider = OpenAIProvider(api_key=api_key)
        return OpenAIChatModel(model_name, provider=provider)
    elif PROVIDER == "anthropic":
        provider = AnthropicProvider(api_key=api_key)
        return AnthropicModel(model_name, provider=provider)
    elif PROVIDER == "google" or PROVIDER == "gemini":
        provider = GoogleProvider(api_key=api_key)
        return GoogleModel(model_name, provider=provider)
    else:
        raise ValueError(f"Unsupported provider: {PROVIDER}. Supported providers: openai, anthropic, google/gemini")

async def get_completion_async(resume_content, job_description_content, api_key, user_prompt: Optional[str] = None):
    """Async version using PydanticAI Agent."""
    model = get_model_instance(api_key)

    # Create PydanticAI Agent with the CV response model
    agent = Agent(
        model,
        output_type=CV,
        system_prompt=(
            "You are a career-coach AI that returns JSON structured according to the provided Pydantic schema. "
            "Your goal is to transform my resume into a concise, impact‑oriented document that mirrors the language of the target job ad."
            "You must NEVER hallucinate or invent any information. Only include details that are explicitly present in the resume. "
            "If a detail is not present in the resume, you must omit it, even if it appears in the job description. "
            "Strictly follow the anti-hallucination rule: do not infer, guess, or add any content from the job description unless it is also present in the resume."
        )
    )

    prompt = _build_prompt(resume_content, job_description_content, user_prompt=user_prompt)
    try:
        # Run the agent with the prompt
        result = await agent.run(prompt)

        # Get the Pydantic model from result
        cv_instance = result.output
        output_dict = cv_instance.model_dump()

        # --- Post-processing hallucination check ---
        resume_lower = resume_content.lower()
        hallucinated_fields = []
        # Check for hallucinated skills
        try:
            skills = output_dict.get('sections', {}).get('Skills', [])
            for entry in skills:
                for detail in entry['details'].split(','):
                    if detail.strip().lower() not in resume_lower and entry['label'].lower() not in resume_lower:
                        hallucinated_fields.append(f"{entry['label']} - {detail.strip()}")
        except Exception:
            pass
        # Warn user if hallucinations detected
        if hallucinated_fields:
            st.warning("Possible hallucinated content detected in the generated CV. Please review these entries and ensure they exist in your original resume:\n" + "\n".join(hallucinated_fields))
        return output_dict
    except ValidationError as e:
        st.error("AI response did not match the required data structure:")
        st.error(e)
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return None

def get_completion(resume_content, job_description_content, api_key, user_prompt: Optional[str] = None):
    """Synchronous wrapper for the async function."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(get_completion_async(resume_content, job_description_content, api_key, user_prompt=user_prompt))

# Cover Letter Generation Function
async def generate_cover_letter_async(
    yaml_resume: str,
    job_description: str,
    api_key: str,
    user_prompt: Optional[str] = None,
) -> str:
    """
    Generate a tailored cover letter using PydanticAI, given the YAML resume and job description.
    Returns the cover letter text or None on error.
    """
    model = get_model_instance(api_key)

    # Create PydanticAI Agent for cover letter generation
    agent = Agent(
        model,
        output_type=str,
        system_prompt="You are a career-coach AI that writes tailored cover letters."
    )

    additional_instructions_section = ""
    if user_prompt:
        additional_instructions_section = f"**Additional User Instructions:**\n{user_prompt}\n---\n"

    prompt = f"""
You are a world-class professional resume writer and career-coach AI. Your mission is to write a compelling, tailored cover letter for a job application.

**Instructions:**
1. Use the provided resume data (YAML format) and job description to craft a cover letter.
2. The cover letter should be highly relevant, concise (max 350 words), and highlight the candidate's fit for the role.
3. Use a professional, engaging tone. Do not hallucinate details not present in the resume.
4. Address the letter to the appropriate role/company if possible (extract from job description).
5. Output only the cover letter text, no formatting or extra commentary.

---
{additional_instructions_section}**Resume YAML:**
{yaml_resume}
---
**Job Description:**
{job_description}
---
"""
    try:
        result = await agent.run(prompt)
        return result.output.strip()
    except Exception as e:
        st.error(f"An error occurred while generating the cover letter: {e}")
        return None

def generate_cover_letter(
    yaml_resume: str,
    job_description: str,
    api_key: str,
    user_prompt: Optional[str] = None,
) -> str:
    """Synchronous wrapper for the async function."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(
        generate_cover_letter_async(
            yaml_resume,
            job_description,
            api_key,
            user_prompt=user_prompt,
        )
    )

st.title("Career Flow - AI Job Application Assistant")

localS = LocalStorage()

# Function to get and set API key in local storage
def get_api_key():
    return localS.getItem("api_key")

def set_api_key(key):
    localS.setItem("api_key", key)

# Get the API key from local storage
stored_api_key = get_api_key()
api_key = st.text_input(
    f"Enter your {PROVIDER.upper()} API Key",
    type="password",
    help="Your API key is stored securely in your browser's local storage.",
    value=stored_api_key if stored_api_key else ""
)

# If the user enters a new key, update it in local storage
if api_key and (api_key != stored_api_key):
    set_api_key(api_key)

if 'output' not in st.session_state:
    st.session_state.output = None
if 'resume_text' not in st.session_state:
    st.session_state.resume_text = ""
if 'yaml_for_editing' not in st.session_state:
    st.session_state.yaml_for_editing = ""
if 'pdf_bytes' not in st.session_state:
    st.session_state.pdf_bytes = None

resume_file = st.file_uploader("Upload your resume (txt or pdf)", type=["txt", "pdf"])
job_description = st.text_area("Paste the job description here")
user_prompt_input = st.text_area(
    "Additional instructions for the AI (optional)",
    help="Add any extra guidance you want the AI to follow beyond the default system instructions.",
)
user_prompt = user_prompt_input.strip() if user_prompt_input else ""

if resume_file is not None:
    if resume_file.type == "application/pdf":
        try:
            with fitz.open(stream=resume_file.read(), filetype="pdf") as doc:
                full_content = []
                for page in doc:
                    # Extract text from the page
                    full_content.append(page.get_text())
                    
                    # Extract URLs from links on the page
                    links = page.get_links()
                    for link in links:
                        if "uri" in link and link["uri"]:
                            full_content.append(link["uri"])
                
                st.session_state.resume_text = "\n".join(full_content)
        except Exception as e:
            st.error(f"Error reading PDF: {e}")
            st.session_state.resume_text = ""
    else:
        st.session_state.resume_text = resume_file.read().decode("utf-8")
    
    if st.session_state.resume_text:
        with st.expander("Click to view the extracted resume text"):
            st.text(st.session_state.resume_text)


if st.button("Generate Tailored Application"):
    if not api_key:
        st.error(f"Please enter your {PROVIDER.upper()} API key to proceed.")
    elif st.session_state.resume_text and job_description:
        if MOCK_TEST:
            with st.spinner("Generating your tailored application... (using mock data)"):
                # For development: Use mock data from the YAML file
                try:
                    with open('temp_cv_c0bd7810-aa7c-44dc-aa2a-7a00ecc587dd.yaml', 'r') as f:
                        mock_data = yaml.safe_load(f)
                    # The output should be the content of the 'cv' key from the yaml
                    resume_data = mock_data.get('cv')
                    if not resume_data:
                        st.error("Mock YAML file is missing the 'cv' key.")
                        resume_data = None
                except FileNotFoundError:
                    st.error("Mock data file not found: temp_cv_c0bd7810-aa7c-44dc-aa2a-7a00ecc587dd.yaml")
                    resume_data = None
                except Exception as e:
                    st.error(f"Error loading mock data: {e}")
                    resume_data = None

                st.session_state.output = resume_data
        else:
            with st.spinner("Generating your tailored application..."):
                resume_data = get_completion(
                    st.session_state.resume_text,
                    job_description,
                    api_key,
                    user_prompt=user_prompt or None,
                )
                st.session_state.output = resume_data
        
        if st.session_state.output:
            # Construct the full data structure for YAML
            generated_cv_content = st.session_state.output
            # Remove empty sections from the generated CV content
            generated_cv_content['sections'] = {
                k: v for k, v in generated_cv_content['sections'].items() if v is not None
            }
            full_cv_data = {
                "cv": generated_cv_content,
                "design": {
                    "theme": "engineeringresumes",
                    "page": {
                        "top_margin": "1cm",
                        "bottom_margin": "1cm",
                        "left_margin": "1cm",
                        "right_margin": "1cm",
                        "show_last_updated_date": False
                    },
                    "text": {
                        "font_size": "10pt",
                        "leading": "0.5em"
                    },
                    "header": {
                        "horizontal_space_between_connections": "0.2cm",
                        "vertical_space_between_name_and_connections": "0.2cm"
                    },
                    "section_titles": {
                        "vertical_space_above": "0.4cm",
                        "vertical_space_below": "0.2cm"
                    },
                    "entries": {
                        "vertical_space_between_entries": "0.8em",
                        "date_and_location_width": "3.5cm"
                    },
                    "highlights": {
                        "vertical_space_between_highlights": "0.2cm"
                    },
                    "entry_types": {
                        "one_line_entry": {
                            "template": "**LABEL:** DETAILS"
                        },
                        "education_entry": {
                            "main_column_first_row_template": "**INSTITUTION**, DEGREE in AREA -- LOCATION",
                            "degree_column_template": None,
                            "degree_column_width": "1cm",
                            "main_column_second_row_template": "SUMMARY\nHIGHLIGHTS",
                            "date_and_location_column_template": "DATE"
                        },
                        "normal_entry": {
                            "main_column_first_row_template": "**NAME** -- **URL**",
                            "main_column_second_row_template": "SUMMARY\nHIGHLIGHTS",
                            "date_and_location_column_template": "DATE"
                        },
                        "experience_entry": {
                            "main_column_first_row_template": "**POSITION**, COMPANY -- LOCATION",
                            "main_column_second_row_template": "SUMMARY\nHIGHLIGHTS",
                            "date_and_location_column_template": "DATE"
                        },
                        "publication_entry": {
                            "main_column_first_row_template": "**TITLE**",
                            "main_column_second_row_template": "AUTHORS\nURL (JOURNAL)",
                            "main_column_second_row_without_journal_template": "AUTHORS\nURL",
                            "main_column_second_row_without_url_template": "AUTHORS\nJOURNAL",
                            "date_and_location_column_template": "DATE"
                        }
                    }
                },
                "locale": {
                    "language": "en"
                }
            }
            cleaned_data, ats_issues = ats_clean_data(full_cv_data)
            yaml_str = yaml.dump(cleaned_data, default_flow_style=False, sort_keys=False)
            st.session_state.yaml_for_editing = yaml_str
            st.session_state.ats_audit_issues = ats_issues
            st.session_state.pdf_bytes = None # Clear any previously generated PDF
        else:
            st.session_state.yaml_for_editing = ""
            st.session_state.ats_audit_issues = []
    else:
        st.error("Please upload a resume and paste a job description.")

if st.session_state.yaml_for_editing:
    st.markdown("---")
    st.subheader("Edit Generated Resume Data (YAML)")
    # ATS Audit Report
    ats_issues = st.session_state.get('ats_audit_issues', [])
    if ats_issues:
        st.warning("**ATS Audit Report:**\n" + "\n".join(f"- {issue}" for issue in ats_issues))
    else:
        st.info("ATS Audit: No major issues detected. Your resume should be ATS-friendly.")
    
    # Using a key helps Streamlit manage the state of this component better.
    # The code_editor component returns a dictionary with the edited text and button clicks.
    response_dict = code_editor(
        st.session_state.yaml_for_editing,
        lang="yaml",
        height=400,
        key="yaml_editor",
        buttons=[{
            "name": "Generate PDF",
            "feather": "Play",
            "primary": True,
            "hasText": True,
            "showWithIcon": True,
            "commands": ["submit"],
            "style": {"bottom": "0.44rem", "right": "0.4rem"}
        }],
        response_mode="debounce"
    )

    # The component can return an empty text value on certain reruns.
    # We only update the session state if the returned text is not empty.
    if response_dict['text'] and response_dict['text'] != st.session_state.yaml_for_editing:
        st.session_state.yaml_for_editing = response_dict['text']
        st.session_state.pdf_bytes = None # Clear old PDF on edit

# AI Auto-Fix Function
async def fix_yaml_with_ai_async(yaml_content: str, error_message: str, api_key: str) -> str:
    """
    Uses the AI to fix a broken YAML file based on an error message.
    """
    model = get_model_instance(api_key)
    agent = Agent(
        model,
        output_type=str,
        system_prompt=(
            "You are an expert YAML debugger for RenderCV. "
            "Your task is to fix the provided YAML content so that it resolves the reported error. "
            "Return ONLY the fixed YAML content. Do not include any markdown formatting (like ```yaml), explanations, or comments. "
            "Ensure the output is valid YAML."
        )
    )
    
    prompt = f"""
    The following YAML content failed to generate a PDF with RenderCV.
    
    **Error Message:**
    {error_message}
    
    **Broken YAML:**
    {yaml_content}
    
    Please fix the YAML to resolve the error.
    """
    
    try:
        result = await agent.run(prompt)
        # Clean up potential markdown formatting if the model ignores instructions
        cleaned_output = result.output.strip()
        if cleaned_output.startswith("```yaml"):
            cleaned_output = cleaned_output[7:]
        if cleaned_output.startswith("```"):
            cleaned_output = cleaned_output[3:]
        if cleaned_output.endswith("```"):
            cleaned_output = cleaned_output[:-3]
        return cleaned_output.strip()
    except Exception as e:
        st.error(f"AI Auto-Fix failed: {e}")
        return None

def fix_yaml_with_ai(yaml_content: str, error_message: str, api_key: str) -> str:
    """Synchronous wrapper for the async function."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(fix_yaml_with_ai_async(yaml_content, error_message, api_key))

# ... inside the button click handler ...
    # Check if the 'Generate PDF' button was clicked.
    if response_dict['type'] == "submit":
        with st.spinner("Generating PDF from edited YAML..."):
            # Use the most up-to-date YAML from the session state
            yaml_string = st.session_state.yaml_for_editing
            if not yaml_string:
                st.error("Cannot generate PDF from empty YAML. Please ensure there is content in the editor.")
            else:
                # --- Validation & Auto-Fix Step ---
                try:
                    from validator import CVValidator
                    # Load YAML to dict
                    data = yaml.safe_load(yaml_string)
                    
                    # Run validation and fix
                    fixed_data, issues = CVValidator.validate_and_fix(data)
                    
                    # If data was modified, update the YAML string
                    if fixed_data != data:
                        yaml_string = yaml.dump(fixed_data, default_flow_style=False, sort_keys=False)
                        
                except Exception as val_e:
                    st.warning(f"Validation warning: {val_e}. Proceeding with original data.")

                # Retry loop for AI Auto-Fix
                max_retries = 1
                attempt = 0
                success = False
                
                while attempt <= max_retries and not success:
                    attempt += 1
                    yaml_file_name = None
                    try:
                        # 1. Create a temporary YAML file
                        yaml_file_name = f"temp_cv_{uuid.uuid4()}.yaml"
                        with open(yaml_file_name, 'w') as f:
                            f.write(yaml_string)

                        output_file_path = "tailored_resume.pdf"
                        
                        # 2. Run RenderCV's render command directly from Python
                        render_output_buffer = io.StringIO()
                        render_failed = False
                        render_message = ""
                        try:
                            with contextlib.redirect_stdout(render_output_buffer), contextlib.redirect_stderr(render_output_buffer):
                                cli_command_render(
                                    input_file_name=yaml_file_name,
                                    pdf_path=output_file_path,
                                    dont_generate_markdown=True,
                                    dont_generate_html=True,
                                    dont_generate_png=True
                                )
                        except SystemExit as render_exit:
                            render_message = render_output_buffer.getvalue()
                            if render_exit.code != 0:
                                render_failed = True
                                if not render_message.strip():
                                    render_message = f"RenderCV exited with code {render_exit.code}."
                        except Exception as render_exception:
                            render_message = render_output_buffer.getvalue().strip() or str(render_exception)
                            render_failed = True
                        else:
                            render_message = render_output_buffer.getvalue()

                        if render_failed:
                            # Filter out the "Welcome" message to show the actual error
                            clean_message = render_message.replace("Welcome to RenderCV! Some useful links:", "").strip()
                            clean_message = re.sub(r'https?://\S+', '', clean_message)
                            
                            # If we have retries left and an API key, try to fix it with AI
                            if attempt <= max_retries and api_key:
                                st.warning(f"PDF generation failed. Attempting AI Auto-Fix (Attempt {attempt}/{max_retries})...")
                                fixed_yaml = fix_yaml_with_ai(yaml_string, clean_message, api_key)
                                if fixed_yaml:
                                    yaml_string = fixed_yaml
                                    st.session_state.yaml_for_editing = fixed_yaml # Update editor
                                    st.success("AI applied a fix. Retrying generation...")
                                    continue # Retry loop
                                else:
                                    st.error("AI Auto-Fix could not resolve the issue.")
                            
                            st.session_state.pdf_bytes = None
                            st.error("RenderCV could not generate the PDF. See details below:")
                            
                            if clean_message:
                                st.code(clean_message, language="text")
                            else:
                                st.error("Unknown error occurred in RenderCV.")
                        else:
                            # 3. Check if the file was created and is not empty
                            if os.path.exists(output_file_path) and os.path.getsize(output_file_path) > 0:
                                with open(output_file_path, "rb") as pdf_file:
                                    st.session_state.pdf_bytes = pdf_file.read()
                                success = True
                            else:
                                st.error("PDF generation via CLI function failed. The output file is missing, empty, or corrupt.")
                                st.session_state.pdf_bytes = None
                                if os.path.exists(output_file_path):
                                    st.error(f"The file `{output_file_path}` was created but has a size of {os.path.getsize(output_file_path)} bytes.")

                    except Exception as e:
                        st.error(f"An unexpected error occurred during PDF generation: {e}")
                        st.session_state.pdf_bytes = None
                    finally:
                        # 4. Clean up the temporary YAML file
                        if yaml_file_name and os.path.exists(yaml_file_name):
                            os.remove(yaml_file_name)
    
    # Display the PDF if it exists in the session state
    if st.session_state.pdf_bytes:
        st.subheader("Tailored Resume Preview")
        pdf_viewer(st.session_state.pdf_bytes, width="100%", height=1000)
        st.download_button(
            label="Download Tailored Resume as PDF",
            data=st.session_state.pdf_bytes,
            file_name="tailored_resume.pdf",
            mime="application/pdf"
        )

    # --- Cover Letter Generation Section ---
    st.markdown("---")
    st.subheader("Generate Tailored Cover Letter")
    if 'cover_letter' not in st.session_state:
        st.session_state.cover_letter = ""

    if st.button("Generate Cover Letter"):
        if not api_key:
            st.error(f"Please enter your {PROVIDER.upper()} API key to proceed.")
        elif not st.session_state.yaml_for_editing or not job_description:
            st.error("YAML resume and job description are required to generate a cover letter.")
        else:
            with st.spinner("Generating your tailored cover letter..."):
                cover_letter = generate_cover_letter(
                    st.session_state.yaml_for_editing,
                    job_description,
                    api_key,
                    user_prompt=user_prompt or None,
                )
                if cover_letter:
                    st.session_state.cover_letter = cover_letter
                else:
                    st.session_state.cover_letter = ""

    if st.session_state.cover_letter:
        st.markdown("**Your Tailored Cover Letter:**")
        st.text_area("Cover Letter", value=st.session_state.cover_letter, height=300)
