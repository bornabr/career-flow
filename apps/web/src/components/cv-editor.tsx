"use client";

import { Trash2 } from "lucide-react";

import { useAppStore } from "@/lib/store";
import type { CV, EducationEntry, ExperienceEntry, OneLineEntry, PersonalProjectEntry, SocialNetwork } from "@/lib/types";
import { createEmptyEducation, createEmptyExperience, createEmptyProject, createEmptySkill } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";

function ensureArray<T>(value: T[] | null | undefined): T[] {
  return Array.isArray(value) ? value : [];
}

export function CVEditor() {
  const { cvData, setCvData, setStep } = useAppStore();

  if (!cvData) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>No CV data yet</CardTitle>
          <CardDescription>Generate a CV draft first to edit it here.</CardDescription>
        </CardHeader>
        <CardContent>
          <Button onClick={() => setStep("upload")}>Back to Upload</Button>
        </CardContent>
      </Card>
    );
  }

  const updateCv = (updater: (current: CV) => CV) => setCvData(updater(cvData));
  const summaryText = ensureArray(cvData.sections.Summary).join("\n");
  const projects = ensureArray(cvData.sections.PersonalProjects);

  const updateSummary = (value: string) => {
    const lines = value.split("\n").map((line) => line.trim()).filter(Boolean);
    updateCv((current) => ({
      ...current,
      sections: { ...current.sections, Summary: lines.length ? lines : [""] },
    }));
  };

  const updateSocial = (index: number, key: keyof SocialNetwork, value: string) => {
    updateCv((current) => ({
      ...current,
      social_networks: ensureArray(current.social_networks).map((item, i) => (i === index ? { ...item, [key]: value } : item)),
    }));
  };

  const updateSkill = (index: number, key: keyof OneLineEntry, value: string) => {
    updateCv((current) => ({
      ...current,
      sections: {
        ...current.sections,
        Skills: current.sections.Skills.map((item, i) => (i === index ? { ...item, [key]: value } : item)),
      },
    }));
  };

  const updateExperienceField = (index: number, key: keyof ExperienceEntry, value: string) => {
    updateCv((current) => ({
      ...current,
      sections: {
        ...current.sections,
        Experience: current.sections.Experience.map((item, i) => (i === index ? { ...item, [key]: value } : item)),
      },
    }));
  };

  const updateExperienceHighlight = (experienceIndex: number, highlightIndex: number, value: string) => {
    updateCv((current) => ({
      ...current,
      sections: {
        ...current.sections,
        Experience: current.sections.Experience.map((item, i) => {
          if (i !== experienceIndex) {
            return item;
          }
          return {
            ...item,
            highlights: item.highlights.map((highlight, hIndex) => (hIndex === highlightIndex ? value : highlight)),
          };
        }),
      },
    }));
  };

  const updateEducationField = (index: number, key: keyof EducationEntry, value: string) => {
    updateCv((current) => ({
      ...current,
      sections: {
        ...current.sections,
        Education: current.sections.Education.map((item, i) => (i === index ? { ...item, [key]: value } : item)),
      },
    }));
  };

  const updateEducationHighlight = (educationIndex: number, highlightIndex: number, value: string) => {
    updateCv((current) => ({
      ...current,
      sections: {
        ...current.sections,
        Education: current.sections.Education.map((item, i) => {
          if (i !== educationIndex) {
            return item;
          }
          return {
            ...item,
            highlights: ensureArray(item.highlights).map((highlight, hIndex) => (hIndex === highlightIndex ? value : highlight)),
          };
        }),
      },
    }));
  };

  const updateProjectField = (index: number, key: keyof PersonalProjectEntry, value: string) => {
    updateCv((current) => ({
      ...current,
      sections: {
        ...current.sections,
        PersonalProjects: ensureArray(current.sections.PersonalProjects).map((item, i) => (i === index ? { ...item, [key]: value } : item)),
      },
    }));
  };

  const updateProjectHighlight = (projectIndex: number, highlightIndex: number, value: string) => {
    updateCv((current) => ({
      ...current,
      sections: {
        ...current.sections,
        PersonalProjects: ensureArray(current.sections.PersonalProjects).map((item, i) => {
          if (i !== projectIndex) {
            return item;
          }
          return {
            ...item,
            highlights: ensureArray(item.highlights).map((highlight, hIndex) => (hIndex === highlightIndex ? value : highlight)),
          };
        }),
      },
    }));
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Contact Information</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2"><Label>Full name</Label><Input value={cvData.name} onChange={(event) => updateCv((current) => ({ ...current, name: event.target.value }))} /></div>
            <div className="space-y-2"><Label>Location</Label><Input value={cvData.location} onChange={(event) => updateCv((current) => ({ ...current, location: event.target.value }))} /></div>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2"><Label>Email</Label><Input value={cvData.email ?? ""} onChange={(event) => updateCv((current) => ({ ...current, email: event.target.value }))} /></div>
            <div className="space-y-2"><Label>Phone</Label><Input value={cvData.phone ?? ""} onChange={(event) => updateCv((current) => ({ ...current, phone: event.target.value }))} /></div>
          </div>
          <div className="space-y-2"><Label>Website</Label><Input value={cvData.website ?? ""} onChange={(event) => updateCv((current) => ({ ...current, website: event.target.value }))} /></div>
          <Separator />
          <div className="space-y-3">
            <div className="flex items-center justify-between"><h3 className="text-sm font-semibold">Social Networks</h3><Button variant="outline" onClick={() => updateCv((current) => ({ ...current, social_networks: [...ensureArray(current.social_networks), { network: "", username: "" }] }))}>+ Add Social</Button></div>
            {ensureArray(cvData.social_networks).map((social, index) => (
              <div key={`social-${index}`} className="grid gap-2 rounded-lg border p-3 md:grid-cols-[1fr_1fr_auto] md:items-end">
                <div className="space-y-2"><Label>Network</Label><Input value={social.network} onChange={(event) => updateSocial(index, "network", event.target.value)} /></div>
                <div className="space-y-2"><Label>Username / URL</Label><Input value={social.username} onChange={(event) => updateSocial(index, "username", event.target.value)} /></div>
                <Button variant="ghost" size="icon" onClick={() => updateCv((current) => ({ ...current, social_networks: ensureArray(current.social_networks).filter((_, i) => i !== index) }))}><Trash2 className="size-4" /></Button>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Summary</CardTitle></CardHeader>
        <CardContent><Textarea className="min-h-28" value={summaryText} onChange={(event) => updateSummary(event.target.value)} /></CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Skills</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          {cvData.sections.Skills.map((skill, index) => (
            <div key={`skill-${index}`} className="grid gap-2 rounded-lg border p-3 md:grid-cols-[1fr_2fr_auto] md:items-end">
              <div className="space-y-2"><Label>Label</Label><Input value={skill.label} onChange={(event) => updateSkill(index, "label", event.target.value)} /></div>
              <div className="space-y-2"><Label>Details</Label><Input value={skill.details} onChange={(event) => updateSkill(index, "details", event.target.value)} /></div>
              <Button variant="ghost" size="icon" onClick={() => updateCv((current) => ({ ...current, sections: { ...current.sections, Skills: current.sections.Skills.filter((_, i) => i !== index) } }))}><Trash2 className="size-4" /></Button>
            </div>
          ))}
          <Button variant="outline" onClick={() => updateCv((current) => ({ ...current, sections: { ...current.sections, Skills: [...current.sections.Skills, createEmptySkill()] } }))}>+ Add Skill</Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Experience</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          {cvData.sections.Experience.map((experience, index) => (
            <div key={`exp-${index}`} className="space-y-4 rounded-xl border p-4">
              <div className="flex items-center justify-between"><p className="text-sm font-semibold">Experience {index + 1}</p><Button variant="ghost" size="icon" onClick={() => updateCv((current) => ({ ...current, sections: { ...current.sections, Experience: current.sections.Experience.filter((_, i) => i !== index) } }))}><Trash2 className="size-4" /></Button></div>
              <div className="grid gap-3 md:grid-cols-2">
                <div className="space-y-2"><Label>Company</Label><Input value={experience.company} onChange={(event) => updateExperienceField(index, "company", event.target.value)} /></div>
                <div className="space-y-2"><Label>Position</Label><Input value={experience.position} onChange={(event) => updateExperienceField(index, "position", event.target.value)} /></div>
              </div>
              <div className="grid gap-3 md:grid-cols-3">
                <div className="space-y-2"><Label>Location</Label><Input value={experience.location ?? ""} onChange={(event) => updateExperienceField(index, "location", event.target.value)} /></div>
                <div className="space-y-2"><Label>Start date</Label><Input value={experience.start_date ?? ""} onChange={(event) => updateExperienceField(index, "start_date", event.target.value)} /></div>
                <div className="space-y-2"><Label>End date</Label><Input value={experience.end_date ?? ""} onChange={(event) => updateExperienceField(index, "end_date", event.target.value)} /></div>
              </div>
              <div className="space-y-3">
                <div className="flex items-center justify-between"><Label className="text-sm font-semibold">Highlights</Label><Button variant="outline" onClick={() => updateCv((current) => ({ ...current, sections: { ...current.sections, Experience: current.sections.Experience.map((item, i) => i === index ? { ...item, highlights: [...item.highlights, ""] } : item) } }))}>+ Add bullet</Button></div>
                {experience.highlights.map((highlight, hIndex) => (
                  <div key={`exp-h-${index}-${hIndex}`} className="flex items-center gap-2">
                    <Input value={highlight} onChange={(event) => updateExperienceHighlight(index, hIndex, event.target.value)} />
                    <Button variant="ghost" size="icon" onClick={() => updateCv((current) => ({ ...current, sections: { ...current.sections, Experience: current.sections.Experience.map((item, i) => {
                      if (i !== index) {
                        return item;
                      }
                      const highlights = item.highlights.filter((_, x) => x !== hIndex);
                      return { ...item, highlights: highlights.length ? highlights : [""] };
                    }) } }))}><Trash2 className="size-4" /></Button>
                  </div>
                ))}
              </div>
            </div>
          ))}
          <Button variant="outline" onClick={() => updateCv((current) => ({ ...current, sections: { ...current.sections, Experience: [...current.sections.Experience, createEmptyExperience()] } }))}>+ Add Experience</Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Education</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          {cvData.sections.Education.map((education, index) => (
            <div key={`edu-${index}`} className="space-y-4 rounded-xl border p-4">
              <div className="flex items-center justify-between"><p className="text-sm font-semibold">Education {index + 1}</p><Button variant="ghost" size="icon" onClick={() => updateCv((current) => ({ ...current, sections: { ...current.sections, Education: current.sections.Education.filter((_, i) => i !== index) } }))}><Trash2 className="size-4" /></Button></div>
              <div className="grid gap-3 md:grid-cols-2">
                <div className="space-y-2"><Label>Institution</Label><Input value={education.institution} onChange={(event) => updateEducationField(index, "institution", event.target.value)} /></div>
                <div className="space-y-2"><Label>Area</Label><Input value={education.area} onChange={(event) => updateEducationField(index, "area", event.target.value)} /></div>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <div className="space-y-2"><Label>Degree</Label><Input value={education.degree ?? ""} onChange={(event) => updateEducationField(index, "degree", event.target.value)} /></div>
                <div className="space-y-2"><Label>Location</Label><Input value={education.location ?? ""} onChange={(event) => updateEducationField(index, "location", event.target.value)} /></div>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <div className="space-y-2"><Label>Start date</Label><Input value={education.start_date ?? ""} onChange={(event) => updateEducationField(index, "start_date", event.target.value)} /></div>
                <div className="space-y-2"><Label>End date</Label><Input value={education.end_date ?? ""} onChange={(event) => updateEducationField(index, "end_date", event.target.value)} /></div>
              </div>
              <div className="space-y-3">
                <div className="flex items-center justify-between"><Label className="text-sm font-semibold">Highlights</Label><Button variant="outline" onClick={() => updateCv((current) => ({ ...current, sections: { ...current.sections, Education: current.sections.Education.map((item, i) => i === index ? { ...item, highlights: [...ensureArray(item.highlights), ""] } : item) } }))}>+ Add bullet</Button></div>
                {ensureArray(education.highlights).map((highlight, hIndex) => (
                  <div key={`edu-h-${index}-${hIndex}`} className="flex items-center gap-2">
                    <Input value={highlight} onChange={(event) => updateEducationHighlight(index, hIndex, event.target.value)} />
                    <Button variant="ghost" size="icon" onClick={() => updateCv((current) => ({ ...current, sections: { ...current.sections, Education: current.sections.Education.map((item, i) => i === index ? { ...item, highlights: ensureArray(item.highlights).filter((_, x) => x !== hIndex) } : item) } }))}><Trash2 className="size-4" /></Button>
                  </div>
                ))}
              </div>
            </div>
          ))}
          <Button variant="outline" onClick={() => updateCv((current) => ({ ...current, sections: { ...current.sections, Education: [...current.sections.Education, createEmptyEducation()] } }))}>+ Add Education</Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Personal Projects</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          {projects.length ? projects.map((project, index) => (
            <div key={`project-${index}`} className="space-y-4 rounded-xl border p-4">
              <div className="flex items-center justify-between"><p className="text-sm font-semibold">Project {index + 1}</p><Button variant="ghost" size="icon" onClick={() => updateCv((current) => ({ ...current, sections: { ...current.sections, PersonalProjects: ensureArray(current.sections.PersonalProjects).filter((_, i) => i !== index) } }))}><Trash2 className="size-4" /></Button></div>
              <div className="grid gap-3 md:grid-cols-2">
                <div className="space-y-2"><Label>Name</Label><Input value={project.name} onChange={(event) => updateProjectField(index, "name", event.target.value)} /></div>
                <div className="space-y-2"><Label>URL</Label><Input value={project.url ?? ""} onChange={(event) => updateProjectField(index, "url", event.target.value)} /></div>
              </div>
              <div className="space-y-2"><Label>Summary</Label><Textarea className="min-h-24" value={project.summary} onChange={(event) => updateProjectField(index, "summary", event.target.value)} /></div>
              <div className="space-y-3">
                <div className="flex items-center justify-between"><Label className="text-sm font-semibold">Highlights</Label><Button variant="outline" onClick={() => updateCv((current) => ({ ...current, sections: { ...current.sections, PersonalProjects: ensureArray(current.sections.PersonalProjects).map((item, i) => i === index ? { ...item, highlights: [...ensureArray(item.highlights), ""] } : item) } }))}>+ Add bullet</Button></div>
                {ensureArray(project.highlights).map((highlight, hIndex) => (
                  <div key={`project-h-${index}-${hIndex}`} className="flex items-center gap-2">
                    <Input value={highlight} onChange={(event) => updateProjectHighlight(index, hIndex, event.target.value)} />
                    <Button variant="ghost" size="icon" onClick={() => updateCv((current) => ({ ...current, sections: { ...current.sections, PersonalProjects: ensureArray(current.sections.PersonalProjects).map((item, i) => i === index ? { ...item, highlights: ensureArray(item.highlights).filter((_, x) => x !== hIndex) } : item) } }))}><Trash2 className="size-4" /></Button>
                  </div>
                ))}
              </div>
            </div>
          )) : <p className="text-sm text-muted-foreground">No personal projects yet.</p>}
          <Button variant="outline" onClick={() => updateCv((current) => ({ ...current, sections: { ...current.sections, PersonalProjects: [...ensureArray(current.sections.PersonalProjects), createEmptyProject()] } }))}>+ Add Project</Button>
        </CardContent>
      </Card>

      <div className="flex flex-col gap-3 sm:flex-row sm:justify-between">
        <Button variant="outline" onClick={() => setStep("upload")}>Back to Upload</Button>
      </div>
    </div>
  );
}
