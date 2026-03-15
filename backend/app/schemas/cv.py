from pydantic import BaseModel, Field, HttpUrl


class SocialNetwork(BaseModel):
    network: str
    username: str = Field(..., description="Username for the social network (do not add the whole URL)")


class ExperienceEntry(BaseModel):
    company: str
    position: str
    location: str | None = None
    start_date: str | None = Field(default=None, description="Start date in YYYY-MM format")
    end_date: str | None = Field(default=None, description="End date in YYYY-MM or 'present' format")
    highlights: list[str] = Field(
        ...,
        description="List of action-oriented highlights for the role. Quantify achievements where possible.",
    )
    summary: str | None = Field(
        default=None,
        description="A brief summary of the role. Don't include if not applicable.",
    )


class EducationEntry(BaseModel):
    institution: str
    area: str
    degree: str | None = None
    location: str | None = None
    start_date: str | None = Field(default=None, description="Start date in YYYY-MM format")
    end_date: str | None = Field(default=None, description="End date in YYYY-MM format")
    highlights: list[str] | None = Field(
        default=None,
        description="List of highlights or relevant coursework. Don't include if not applicable.",
    )
    summary: str | None = Field(
        default=None,
        description="A brief summary of the education entry. Don't include if not applicable.",
    )


class OneLineEntry(BaseModel):
    label: str
    details: str


class PersonalProjectEntry(BaseModel):
    name: str
    summary: str = Field(..., description="Brief description of the project, including technologies used and impact.")
    highlights: list[str] | None = Field(
        default=None,
        description="Key achievements or features.",
    )
    url: HttpUrl | None = Field(default=None, description="URL to the project or repository.")


class PublicationsEntry(BaseModel):
    title: str
    authors: list[str]
    doi: str | None = None
    journal: str
    date: str | None = Field(default=None, description="Publication date in YYYY format")
    url: HttpUrl


class Sections(BaseModel):
    Summary: list[str] = Field(
        ...,
        description="A 2-3 sentence professional summary, split into a list of strings.",
    )
    Skills: list[OneLineEntry]
    Education: list[EducationEntry]
    Experience: list[ExperienceEntry]
    AdditionalExperience: list[ExperienceEntry] | None = Field(
        default=None,
        description="Additional experience entries that may not fit the job description.",
    )
    Publications: list[PublicationsEntry] | None = Field(
        default=None,
        description="List of publications. Optional; omit if not applicable.",
    )
    PersonalProjects: list[PersonalProjectEntry] | None = Field(
        default=None,
        description="List of personal projects relevant to the job.",
    )


class CV(BaseModel):
    name: str
    location: str
    email: str | None = None
    phone: str | None = Field(
        default=None,
        pattern=r"^\+?[1-9]\d{1,14}$",
        description="Phone number in E.164 format (e.g., +15555555555)",
    )
    website: HttpUrl | None = None
    social_networks: list[SocialNetwork] | None = None
    sections: Sections


# Rebuild for forward references
CV.model_rebuild()
Sections.model_rebuild()
