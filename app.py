import streamlit as st
import os
from openai import OpenAI
import fitz  # PyMuPDF
import io
import json

def get_completion(resume_content, job_description_content):
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    prompt = f"""You are an expert career coach AI. Your task is to parse a resume and a job description, then generate a complete, tailored resume in a structured JSON format.

Follow these steps:
1. Carefully read the entire resume content provided.
2. Carefully read the job description to understand the required skills and qualifications.
3. From the resume, extract the user's personal information (name, location, email, phone, website) and professional summary.
4. From the resume, extract all sections like "Experience", "Education", and "Skills". Preserve their structure.
5. Focus on the **most recent job experience** listed in the resume. Rewrite its "highlights" (bullet points) to be highly specific and tailored to the requirements mentioned in the job description. Use action verbs and quantify achievements where possible.
6. Return a single JSON object that matches the following structure. Do NOT include any text outside of the JSON object.

JSON Structure:
{{
  "cv": {{
    "name": "string",
    "location": "string",
    "email": "string",
    "phone": "string",
    "website": "string",
    "summary": "string"
  }},
  "sections": {{
    "experience": [
      {{
        "company": "string",
        "position": "string",
        "start_date": "string",
        "end_date": "string",
        "highlights": [
          "string"
        ]
      }}
    ],
    "education": [
      {{
        "institution": "string",
        "area": "string",
        "start_date": "string",
        "end_date": "string"
      }}
    ],
    "skills": [
      {{
        "name": "string",
        "details": "string"
      }}
    ]
  }}
}}

Resume Content:
---
{resume_content}
---

Job Description:
---
{job_description_content}
---
"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a career-coach AI that returns JSON structured like the user requests."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"}
    )
    
    try:
        response_data = json.loads(response.choices[0].message.content)
        return response_data
    except (json.JSONDecodeError, TypeError) as e:
        st.error(f"Error parsing AI response: {e}")
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
        with st.spinner("Generating your tailored application..."):
            resume_data = get_completion(st.session_state.resume_text, job_description)
            st.session_state.output = resume_data
    else:
        st.error("Please upload a resume and paste a job description.")

if st.session_state.output:
    st.markdown("---")
    st.subheader("Generated Resume Data (JSON)")
    st.json(st.session_state.output)
