from datetime import datetime
from pydantic import BaseModel


class Task(BaseModel):
    id: int | None = None
    title: str
    status: str
    category: str
    details_json: dict
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ActionLog(BaseModel):
    id: int | None = None
    name: str
    type: str
    metadata_json: dict
    decision: str
    reason: str
    created_at: datetime | None = None


class Notification(BaseModel):
    id: int | None = None
    level: str
    message: str
    created_at: datetime | None = None


class Experiment(BaseModel):
    id: int | None = None
    name: str
    hypothesis: str
    variants_json: list[str]
    status: str
    started_at: datetime | None = None
    ended_at: datetime | None = None
    outcome_json: dict


class Asset(BaseModel):
    id: int | None = None
    type: str
    platform: str
    title: str
    status: str
    content_md: str
    metadata_json: dict
    created_at: datetime | None = None
    updated_at: datetime | None = None
