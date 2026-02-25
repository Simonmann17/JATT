import os
from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./jatt.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)


def init_db() -> None:
    from . import models  # noqa: F401

    SQLModel.metadata.create_all(bind=engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session

