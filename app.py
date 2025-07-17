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

# Pydantic Models for RenderCV Structure
# These models define the exact structure RenderCV expects.

MOCK_TEST = True  # Set to True for development/testing with mock data

class SocialNetwork(BaseModel):
    network: str
    username: str

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
    summary: Optional[str] = None
    social_networks: Optional[List[SocialNetwork]] = None
    sections: 'Sections'

class ExperienceEntry(BaseModel):
    company: str
    position: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    highlights: List[str]

class EducationEntry(BaseModel):
    institution: str
    area: str
    degree: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class OneLineEntry(BaseModel):
    label: str
    details: str

class Sections(BaseModel):
    Experience: List[ExperienceEntry]
    Education: List[EducationEntry]
    Skills: List[OneLineEntry]

# This is required for Pydantic v1/v2 compatibility for forward references.
CV.model_rebuild()
Sections.model_rebuild()


def get_completion(resume_content, job_description_content):
    # Patch the client with instructor
    client = instructor.patch(OpenAI(api_key=os.environ.get("OPENAI_API_KEY")))

    prompt = f"""You are an expert career coach AI. Your task is to parse a resume and a job description, then generate a complete, tailored resume.
The output must be a JSON object that strictly follows the defined schema.

- Extract all personal information, professional summary, work experiences, education, and skills from the resume.
- If an information like phone, website, etc was not available don't include it.
- Focus on tailoring the highlights of the **most recent job experience** to align with the requirements in the job description.
- Ensure the output is a valid instance of the CV model.

Resume Content:
---
{resume_content}
---

Job Description:
---
{job_description_content}
---
"""
    
    try:
        # Use the response_model parameter to get structured output
        cv_instance = client.chat.completions.create(
            model="gpt-4o",
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

if 'output' not in st.session_state:
    st.session_state.output = None
if 'resume_text' not in st.session_state:
    st.session_state.resume_text = ""

resume_file = st.file_uploader("Upload your resume (txt or pdf)", type=["txt", "pdf"])
job_description = st.text_area("Paste the job description here")

if resume_file is not None:
    if resume_file.type == "application/pdf":
        try:
            with fitz.open(stream=resume_file.read(), filetype="pdf") as doc:
                pages = [page.get_text() for page in doc]
                st.session_state.resume_text = "\n".join(pages)
        except Exception as e:
            st.error(f"Error reading PDF: {e}")
            st.session_state.resume_text = ""
    else:
        st.session_state.resume_text = resume_file.read().decode("utf-8")
    
    if st.session_state.resume_text:
        with st.expander("Click to view the extracted resume text"):
            st.text(st.session_state.resume_text)


if st.button("Generate Tailored Application"):
    if st.session_state.resume_text and job_description:
        if MOCK_TEST:
            with st.spinner("Generating your tailored application... (using mock data)"):
                # resume_data = get_completion(st.session_state.resume_text, job_description)
                
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
                resume_data = get_completion(st.session_state.resume_text, job_description)
                st.session_state.output = resume_data
        
    else:
        st.error("Please upload a resume and paste a job description.")

if st.session_state.output:
    st.markdown("---")
    st.subheader("Generated Resume Data (JSON)")
    st.json(st.session_state.output)

    # Generate and download PDF using the CLI command function
    yaml_file_name = None
    try:
        generated_cv_content = st.session_state.output
        full_cv_data = {
            "cv": generated_cv_content,
            "design": {"theme": "classic"},
            "rendercv_settings": {
                "date": datetime.date.today().strftime('%Y-%m-%d')
            },
            "locale": {
                "language": "en"
            }
        }

        # 1. Create a temporary YAML file
        yaml_file_name = f"temp_cv_{uuid.uuid4()}.yaml"
        with open(yaml_file_name, 'w') as f:
            yaml.dump(full_cv_data, f, default_flow_style=False, sort_keys=False)

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
                pdf_bytes = pdf_file.read()

            st.download_button(
                label="Download Tailored Resume as PDF",
                data=pdf_bytes,
                file_name="tailored_resume.pdf",
                mime="application/pdf"
            )
        else:
            st.error("PDF generation via CLI function failed. The output file is missing, empty, or corrupt.")
            if os.path.exists(output_file_path):
                st.error(f"The file `{output_file_path}` was created but has a size of {os.path.getsize(output_file_path)} bytes.")

    except Exception as e:
        st.error(f"An unexpected error occurred during PDF generation: {e}")
    finally:
        # 4. Clean up the temporary YAML file
        if yaml_file_name and os.path.exists(yaml_file_name):
            os.remove(yaml_file_name)