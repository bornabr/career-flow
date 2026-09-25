#import "layout.typ": resume

// Synthetic data only. Copy this file into an output directory and replace every
// claim with evidence from the private data repo before creating a real resume.
#resume(
  (name: "Alex Example", headline: "Software Engineer", contact: (
    "Toronto, ON", "alex@example.com", "example.com/alex",
  )),
  summary: [Software engineer focused on *reliable data systems* and Python services.],
  skills: (
    (label: "Programming", items: ("Python", "SQL")),
    (label: "Data systems", items: ("Monitoring", "Data quality")),
  ),
  experience: (
    (title: "Software Engineer", org: "Example Company", dates: "2023 - Present", bullets: (
      [Built *Python monitoring* for data pipelines so analysts could investigate failed loads.],
      [Reworked the retry path for those loads, reducing failed runs by 30%.],
    )),
  ),
  projects: (
    (title: "Data Quality Toolkit", dates: "2024", bullets: (
      "Created automated checks and a dashboard for pipeline health.",
    )),
  ),
  education: (
    (credential: "BSc, Computer Science", org: "Example University", dates: "2018 - 2022"),
  ),
  publications: (
    (citation: [Example research paper, 2022.], paper_url: "https://example.com/paper", code_url: "https://github.com/example/example-paper"),
  ),
)
