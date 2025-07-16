import argparse
import os
from openai import OpenAI

def main():
    parser = argparse.ArgumentParser(description="Tailor a resume and draft a cover letter.")
    parser.add_argument("resume", help="Path to the resume file.")
    parser.add_argument("job_description", help="Path to the job description file.")
    args = parser.parse_args()

    with open(args.resume, 'r') as f:
        resume_content = f.read()
    with open(args.job_description, 'r') as f:
        job_description_content = f.read()

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

    output_content = response.choices[0].message.content

    with open("tailored_application.md", "w") as f:
        f.write(output_content)

    print("Successfully created tailored_application.md")

if __name__ == "__main__":
    main()
