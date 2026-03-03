from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class ApplicationBase(SQLModel):
    vendor: str = Field(index=True)
    subject: str = Field(default="", index=True)
    job_title: Optional[str] = None
    company: Optional[str] = Field(default=None, index=True)
    location: Optional[str] = None
    status: Optional[str] = Field(default=None, index=True)
    requisition_id: Optional[str] = Field(default=None, index=True)
    applied_at: Optional[datetime] = None
    email_received_at: datetime = Field(default_factory=datetime.utcnow)


class Application(ApplicationBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    raw_email: str


class ApplicationCreate(ApplicationBase):
    raw_email: str


class ApplicationRead(ApplicationBase):
    id: int

