import streamlit as st
import os
from openai import OpenAI
import fitz  # PyMuPDF
import io
import json
from pydantic import BaseModel, Field, ValidationError, HttpUrl
from typing import List, Optional
import instructor
import datetime
import subprocess
import yaml
import uuid
from rendercv.cli.commands import cli_command_render
import base64
from code_editor import code_editor
from streamlit_local_storage import LocalStorage

# Pydantic Models for RenderCV Structure
# These models define the exact structure RenderCV expects.

MOCK_TEST = False  # Set to True for development/testing with mock data

class SocialNetwork(BaseModel):
    network: str
    username: str = Field(..., description="Username for the social network (do not add the whole URL)")

class CV(BaseModel):
    name: str
    location: str
    email: Optional[str] = None
    phone: str = Field(
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

class EducationEntry(BaseModel):
    institution: str
    area: str
    degree: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[str] = Field(default=None, description="Start date in YYYY-MM format")
    end_date: Optional[str] = Field(default=None, description="End date in YYYY-MM format")
    highlights: Optional[List[str]] = Field(default=None, description="List of highlights or relevant coursework. Tailor these to the job description. Don't include if not applicable.")

class OneLineEntry(BaseModel):
    label: str
    details: str

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
    Publications: List[PublicationsEntry]

# This is required for Pydantic v1/v2 compatibility for forward references.
CV.model_rebuild()
Sections.model_rebuild()

def _build_prompt(resume: str, job_desc: str) -> str:
    """Construct the system/user prompt with strict instructions.

    The prompt enforces:
    - Schema compliance
    - No hallucination
    - Irrelevant content filtering
    - Highlight merging/splitting guidelines
    """

    return f"""
**Role**: You are a world-class professional resume writer and career-coach AI. Your mission is to transform a generic resume into a highly-tailored, compelling CV optimized for a specific job description.

**Objective**: Produce **one** JSON object that conforms **exactly** to the provided Pydantic and rendercv (v2) schema.

---
**Non-Negotiable Constraints**
1. **Schema Fidelity** - Output **must** be valid JSON matching the `CV` model (no extra keys).
2. **No Hallucination** - Omit any detail not present in the resume. If a field is missing, leave it out.
3. **Relevancy Filter** - Include *only* experience, skills, and education that directly or indirectly support the job description. Drop the rest.
4. **Highlights Hygiene** -
   - Split overly long or compound highlights into concise bullets (≤2 lines each).
   - Each Experience can have upto 4 highlights for recent roles and 3 for older roles.
5. **Action Verbs & Metrics** - Start bullets with strong verbs (e.g., "Led", "Architected") and quantify impact when possible (e.g., "Increased efficiency by 30%," "Managed a team of 5"). 
6. **Markdown Emphasis** - Bold (`**`) any keyword that *exactly* matches a skill or responsibility from the job description (in `highlights` & `summary`).
7. **Date Format** - Use YYYY-MM, YYYY, or "present" exactly as defined in the schema.
8. **Username Extraction** - Return only usernames for social links (e.g., GitHub, LinkedIn).
9. **Single-Page Target** - Keep the final CV to about **one page** (≈500-600 words when rendered). Trim or omit less critical details to fit including old experiences, non-relevant skills, and other extraneous information.

---
**Step-by-Step Process (internal - do not output)**
1. **Analyse Inputs** - Identify the 5-7 most critical keywords/skills from the Job Description that are strongly relavant to the user's background. Map resume content to those.
2. **Synthesise Content** -
   - **Summary** - 2-3 sentences (≤3 lines totally) that pitch the candidate using those keywords.
   - **Experience** - Rewrite recent roles; keep or remove older ones based on relevance. Ensure highlights follow Constraint 4 and overall length supports the single-page goal.
   - **Skills** - Present only relevant skills, grouped under clear labels. Add missing JD keywords (**bolded**) if absent in resume but seems suitable.
   - **Education** - Generally does not need any highlights. Only include entries when they directly strengthen candidacy for the role.
3. **Assemble JSON** - Populate the `CV` object and return *only* the JSON.

---
**Resume Content**:
{resume}
---
**Job Description**:
{job_desc}
---
"""

def get_completion(resume_content, job_description_content, api_key):
    # Patch the client with instructor
    client = instructor.patch(OpenAI(api_key=api_key))

    prompt = _build_prompt(resume_content, job_description_content)
    
    try:
        # Use the response_model parameter to get structured output
        cv_instance = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": "You are a career-coach AI that returns JSON structured according to the provided Pydantic schema."},
                {"role": "user", "content": prompt}
            ],
            response_model=CV,
        )
        # The response is already a Pydantic object, so we convert it to a dict
        return cv_instance.model_dump()
        
    except ValidationError as e:
        st.error("AI response did not match the required data structure:")
        st.error(e)
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return None

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
    "Enter your OpenAI API Key", 
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
        st.error("Please enter your OpenAI API key to proceed.")
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
                resume_data = get_completion(st.session_state.resume_text, job_description, api_key)
                st.session_state.output = resume_data
        
        if st.session_state.output:
            # Construct the full data structure for YAML
            generated_cv_content = st.session_state.output
            full_cv_data = {
                "cv": generated_cv_content,
                "design": {
                    "theme": "engineeringresumes",
                    "page": {
                        "top_margin": "1cm",
                        "bottom_margin": "1cm",
                        "left_margin": "1cm",
                        "right_margin": "1cm"
                    },
                    "text": {
                        "font_size": "10pt",
                        "leading": "0.5em"
                    },
                    "header": {
                        "horizontal_space_between_connections": "0.2cm",
                    },
                    "entries": {
                        "vertical_space_between_entries": "0.8em",
                        "date_and_location_width": "3.5cm"
                    },
                    "highlights": {
                        "vertical_space_between_highlights": "0.2cm"
                    }
                },
                "locale": {
                    "language": "en"
                }
            }
            st.session_state.yaml_for_editing = yaml.dump(full_cv_data, default_flow_style=False, sort_keys=False)
            st.session_state.pdf_bytes = None # Clear any previously generated PDF
        else:
            st.session_state.yaml_for_editing = ""
    else:
        st.error("Please upload a resume and paste a job description.")

if st.session_state.yaml_for_editing:
    st.markdown("---")
    st.subheader("Edit Generated Resume Data (YAML)")
    
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

    # Check if the 'Generate PDF' button was clicked.
    if response_dict['type'] == "submit":
        with st.spinner("Generating PDF from edited YAML..."):
            # Use the most up-to-date YAML from the session state
            yaml_string = st.session_state.yaml_for_editing
            if not yaml_string:
                st.error("Cannot generate PDF from empty YAML. Please ensure there is content in the editor.")
            else:
                yaml_file_name = None
                try:
                    # 1. Create a temporary YAML file
                    yaml_file_name = f"temp_cv_{uuid.uuid4()}.yaml"
                    with open(yaml_file_name, 'w') as f:
                        f.write(yaml_string)

                    output_file_path = "tailored_resume.pdf"
                    
                    # 2. Run RenderCV's render command directly from Python
                    cli_command_render(
                        input_file_name=yaml_file_name,
                        pdf_path=output_file_path,
                        dont_generate_markdown=True,
                        dont_generate_html=True,
                        dont_generate_png=True
                    )

                    # 3. Check if the file was created and is not empty
                    if os.path.exists(output_file_path) and os.path.getsize(output_file_path) > 0:
                        with open(output_file_path, "rb") as pdf_file:
                            st.session_state.pdf_bytes = pdf_file.read()
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
        # Embed PDF viewer
        base64_pdf = base64.b64encode(st.session_state.pdf_bytes).decode('utf-8')
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="800" height="1000" type="application/pdf"></iframe>'
        
        st.subheader("Tailored Resume Preview")
        st.markdown(pdf_display, unsafe_allow_html=True)

        # Also provide a download button
        st.download_button(
            label="Download Tailored Resume as PDF",
            data=st.session_state.pdf_bytes,
            file_name="tailored_resume.pdf",
            mime="application/pdf"
        )