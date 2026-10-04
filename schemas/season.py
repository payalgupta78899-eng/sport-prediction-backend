from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional


class SeasonCreate(BaseModel):
    name        : str
    description : Optional[str] = None
    start_date  : datetime
    end_date    : datetime

    @field_validator("end_date")
    def end_after_start(cls, v, info):
        if "start_date" in info.data and v <= info.data["start_date"]:
            raise ValueError("end_date must be after start_date")
        return v


class SeasonResponse(BaseModel):
    id          : int
    name        : str
    description : Optional[str]
    start_date  : datetime
    end_date    : datetime
    is_active   : bool
    created_at  : datetime

    class Config:
        from_attributes = True
