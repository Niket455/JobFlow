from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class CareerGoalData(BaseModel):
    target_role: str | None = None
    target_salary_min: int | None = None
    currency: str = "INR"
    locations: list[str] = []
    experience_band: str | None = None
    target_date: date | None = None


class CareerGoalRead(CareerGoalData):
    model_config = ConfigDict(from_attributes=True)

    updated_at: datetime | None = None
