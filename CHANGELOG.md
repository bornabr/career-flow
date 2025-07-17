# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2025-07-16

### Added
- **Stage 1: "Hello–Cover-Letter" Proof-of-Concept**
  - Created `tailor.py` script to generate a tailored résumé and cover letter from a résumé and job description.
  - Uses a single prompt to an LLM (gpt-4o-mini).
  - Outputs the result to a Markdown file (`tailored_application.md`).
  - Added `resume.txt` and `job_description.txt` as example inputs.
  - Initialized project with Poetry.

## [0.2.0] - 2025-07-16

### Added
- **Stage 2: Ship an Internal Web MVP (In Progress)**
  - Created a web interface using Streamlit (`app.py`).
  - Users can upload a resume as a `.txt` or `.pdf` file.
  - Users can paste a job description.
  - Implemented PDF text extraction using `PyMuPDF` to preserve layout.
  - The application displays the extracted resume text for verification.

## [0.2.1] - 2025-07-17

### Added
- **Stage 2: Ship an Internal Web MVP (In Progress)**
  - Updated AI prompt to generate a full, structured JSON resume based on the uploaded resume and job description.
  - Implemented OpenAI's JSON mode for reliable, structured output.
  - The application now displays the generated JSON for verification.
