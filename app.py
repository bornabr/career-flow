import streamlit as st
import os
from openai import OpenAI
import fitz  # PyMuPDF
import io

def get_completion(resume_content, job_description_content):
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    prompt = f"""You are a career-coach AI. Rewrite the résumé bullets to emphasize skills the job ad requires; then draft a 250-word cover letter.

Resume:
{resume_content}

Job Description:
{job_description_content}
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a career-coach AI. Rewrite the résumé bullets to emphasize skills the job ad requires; then draft a 250-word cover letter."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

st.title("Career Flow - AI Job Application Assistant")

if 'output' not in st.session_state:
    st.session_state.output = ""
if 'resume_text' not in st.session_state:
    st.session_state.resume_text = ""

resume_file = st.file_uploader("Upload your resume (txt or pdf)", type=["txt", "pdf"])
job_description = st.text_area("Paste the job description here")

if resume_file is not None:
    if resume_file.type == "application/pdf":
        with fitz.open(stream=resume_file.read(), filetype="pdf") as doc:
            pages = [page.get_text() for page in doc]
            st.session_state.resume_text = "\n".join(pages)
    else:
        st.session_state.resume_text = resume_file.read().decode("utf-8")
    
    with st.expander("Click to view the extracted resume text"):
        st.text(st.session_state.resume_text)


if st.button("Generate Tailored Application"):
    if st.session_state.resume_text and job_description:
        with st.spinner("Generating your tailored application..."):
            output = get_completion(st.session_state.resume_text, job_description)
            st.session_state.output = output
    else:
        st.error("Please upload a resume and paste a job description.")

if st.session_state.output:
    st.markdown("---")
    st.subheader("Your Tailored Application")
    st.markdown(st.session_state.output)
