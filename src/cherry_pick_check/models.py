from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class PRState(str, Enum):
    OPEN = "open"
    MERGED = "merged"
    CLOSED = "closed"


class CherryPickStatus(str, Enum):
    PICKED = "picked"
    NOT_PICKED = "not_picked"
    UNKNOWN = "unknown"


class PRInfo(BaseModel):
    number: int
    title: str
    url: str
    author: str
    state: PRState = PRState.MERGED
    created_at: datetime | None = None
    merged_at: datetime | None = None
    base_branch: str


class CherryPickResult(BaseModel):
    source_pr: PRInfo
    target_branch: str
    status: CherryPickStatus
    related_pr: PRInfo | None = None
    detection_method: str = ""
