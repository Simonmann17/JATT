from typing import List

from fastapi import Depends, FastAPI, Query
from sqlmodel import Session, select

from .db import get_session, init_db
from .gmail_client import fetch_workday_emails
from .models import Application, ApplicationCreate, ApplicationRead
from .parsers.workday import parse_workday_email


app = FastAPI(title="JATT Backend", version="0.1.0")


@app.on_event("startup")
async def on_startup() -> None:
    init_db()


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok"}


@app.post("/parse", response_model=ApplicationRead)
async def parse_email(
    payload: ApplicationCreate, session: Session = Depends(get_session)
) -> ApplicationRead:
    # For now we assume vendor is Workday and run the Workday-specific parser.
    parsed = parse_workday_email(payload.raw_email)
    app_row = Application.from_orm(parsed)
    session.add(app_row)
    session.commit()
    session.refresh(app_row)
    return app_row


@app.get("/applications", response_model=List[ApplicationRead])
async def list_applications(session: Session = Depends(get_session)) -> list[ApplicationRead]:
    statement = select(Application).order_by(Application.applied_at.desc())
    results = session.exec(statement).all()
    return results


@app.post("/gmail/import", response_model=List[ApplicationRead])
async def import_from_gmail(
    limit: int = Query(default=5, ge=1, le=100),
    lookback_days: int = Query(default=90, ge=1, le=3650),
    session: Session = Depends(get_session),
) -> List[ApplicationRead]:
    """
    Fetch recent Workday emails from Gmail, parse them, store, and return the records.

    Assumes you have set up Gmail API credentials (see README notes).
    """
    raw_emails = fetch_workday_emails(limit=limit, lookback_days=lookback_days)
    created: list[ApplicationRead] = []

    for raw_email in raw_emails:
        parsed = parse_workday_email(raw_email)
        app_row = Application.from_orm(parsed)
        session.add(app_row)
        session.commit()
        session.refresh(app_row)
        created.append(app_row)

    return created
