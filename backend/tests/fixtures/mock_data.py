"""Mock resume data for testing."""

SAMPLE_RESUME = """
John Doe
john.doe@example.com | (555) 123-4567 | linkedin.com/in/johndoe

EXPERIENCE
Senior Software Engineer, TechCorp (2020-Present)
- Led development of microservices architecture serving 10M+ users
- Reduced API latency by 40% through optimization initiatives
- Mentored 5 junior engineers

Software Engineer, StartupXYZ (2018-2020)
- Built full-stack web application using React and Node.js
- Implemented CI/CD pipeline reducing deployment time by 50%

EDUCATION
BS Computer Science, State University (2018)
GPA: 3.8/4.0

SKILLS
Languages: Python, JavaScript, TypeScript, Go
Frameworks: FastAPI, React, Next.js
Tools: Docker, Kubernetes, PostgreSQL, Redis
"""

SAMPLE_JOB_DESCRIPTION = """
Senior Backend Engineer - AI Platform

We're looking for a Senior Backend Engineer to join our AI Platform team.

Requirements:
- 5+ years of backend development experience
- Strong Python expertise
- Experience with microservices and distributed systems
- Proficiency with FastAPI or similar frameworks
- Experience with LLM integrations or AI systems
- PostgreSQL database experience
- Docker and Kubernetes knowledge

Responsibilities:
- Design and build scalable backend services
- Develop AI/ML integration features
- Collaborate with frontend and data teams
- Implement monitoring and observability
- Mentor junior engineers

Nice to have:
- LangGraph or similar workflow orchestration tools
- Experience with async programming
- GraphQL experience
- AWS or GCP experience
"""

SAMPLE_CV_OUTPUT = {
    "name": "John Doe",
    "contact": {
        "email": "john.doe@example.com",
        "phone": "(555) 123-4567",
        "linkedin": "linkedin.com/in/johndoe"
    },
    "summary": "Senior Software Engineer with 5+ years of experience building scalable microservices and AI-powered systems. Expert in Python, FastAPI, and distributed systems. Proven track record of optimizing performance and mentoring teams.",
    "experience": [
        {
            "title": "Senior Software Engineer",
            "company": "TechCorp",
            "duration": "2020-Present",
            "highlights": [
                "Architected microservices handling 10M+ concurrent users",
                "Optimized API latency by 40% through distributed caching",
                "Mentored 5 engineers in Python and system design"
            ]
        }
    ],
    "skills": ["Python", "FastAPI", "Microservices", "Docker", "Kubernetes", "PostgreSQL", "LLMs"],
    "education": [
        {
            "degree": "BS Computer Science",
            "institution": "State University",
            "year": 2018,
            "gpa": "3.8/4.0"
        }
    ]
}
