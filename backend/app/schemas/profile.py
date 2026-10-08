from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class EducationItem(BaseModel):
    institution: str
    degree: str | None = None
    field_of_study: str | None = None
    start_year: int | None = None
    end_year: int | None = None


class WorkItem(BaseModel):
    company: str
    title: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    description: str | None = None


class ProjectItem(BaseModel):
    name: str
    description: str | None = None
    url: str | None = None
    technologies: list[str] = []


class ProfileData(BaseModel):
    full_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    location: str | None = None
    preferred_locations: list[str] = []
    current_company: str | None = None
    current_role: str | None = None
    summary: str | None = None
    experience_years: float | None = None
    skills: list[str] = []
    target_roles: list[str] = []
    industries: list[str] = []
    companies: list[str] = []
    notice_period_days: int | None = None
    employment_type: str | None = None
    work_mode: str | None = None
    education: list[EducationItem] = []
    work_history: list[WorkItem] = []
    certifications: list[str] = []
    projects: list[ProjectItem] = []
    achievements: list[str] = []


class ProfileRead(ProfileData):
    model_config = ConfigDict(from_attributes=True)

    updated_at: datetime | None = None
