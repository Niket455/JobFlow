from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DealBreakersData(BaseModel):
    min_salary: int | None = None
    excluded_companies: list[str] = []
    excluded_locations: list[str] = []
    no_night_shifts: bool = False


class DealBreakersRead(DealBreakersData):
    model_config = ConfigDict(from_attributes=True)

    updated_at: datetime | None = None
