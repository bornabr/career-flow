// Single-column resume renderer. Keep headings as text for PDF extraction.
// All claims and ordering come from the calling skill's reviewed data file.
#let resume(profile, summary: "", skills: (), experience: (), projects: (), education: (), publications: ()) = {
  set page("us-letter", margin: (x: 0.72in, y: 0.50in))
  set text(font: "New Computer Modern", size: 9.5pt, fill: rgb("202a34"))
  set par(leading: 0.42em)
  show heading.where(level: 2): it => [
    #v(0.65em)
    #text(size: 10pt, weight: "bold", fill: rgb("153c55"))[#it.body]
    #v(-0.45em)
    #line(length: 100%, stroke: 0.5pt + rgb("9daeb8"))
    #v(0.16em)
  ]

  align(center)[
    #text(size: 17pt, weight: "bold")[#profile.name] \
    #if profile.headline != "" { text(size: 10pt)[#profile.headline] }
    #if profile.contact.len() > 0 { [\ #profile.contact.join("  |  ")] }
  ]

  if summary != "" [
    == Summary
    #summary
  ]

  if skills.len() > 0 [
    == Skills
    #for group in skills [
      #text(weight: "bold")[#group.label] #h(0.4em) #group.items.join("  |  ")
      #v(0.12em)
    ]
  ]

  if experience.len() > 0 [
    == Experience
    #for item in experience [
      #assert(item.bullets.len() >= 2, message: "Each experience must have at least two supported bullets.")
      #text(weight: "bold")[#item.title] #h(1fr) #item.dates \
      #item.org
      #for bullet in item.bullets [
        - #bullet
      ]
      #v(0.18em)
    ]
  ]

  if projects.len() > 0 [
    == Projects
    #for item in projects [
      #text(weight: "bold")[#item.title] #h(1fr) #item.dates
      #for bullet in item.bullets [
        - #bullet
      ]
      #v(0.18em)
    ]
  ]

  if education.len() > 0 [
    == Education
    #for item in education [
      #text(weight: "bold")[#item.credential] #h(1fr) #item.dates \
      #item.org
      #v(0.18em)
    ]
  ]

  if publications.len() > 0 [
    == Publications
    #for item in publications [
      - #item.citation #h(0.35em) #if item.paper_url != "" { text(fill: rgb("17689a"))[#link(item.paper_url)[Paper]] } #if item.code_url != "" { [#h(0.25em) #text(fill: rgb("17689a"))[#link(item.code_url)[Code]]] }
    ]
  ]
}
