import logging
import os
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from database.models import Base

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in environment")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _relax_handle_uniqueness() -> None:
    """Drop the UNIQUE index that older deployments have on ``users.handle``.

    ``handle`` used to be unique, which made a GitHub rename — the user takes a new
    login, or someone else takes their old one — fail the next sign-in with an
    IntegrityError. ``create_all`` never alters a table that already exists, so the
    index from the first deployment has to be replaced explicitly. Idempotent: safe
    on every boot, and a no-op on a database created after this change.
    """
    try:
        with engine.begin() as conn:
            conn.execute(text("DROP INDEX IF EXISTS ix_users_handle"))
            if engine.dialect.name == "postgresql":
                # Belt and braces: declared as a table constraint rather than a bare
                # index, the uniqueness would survive the DROP INDEX above.
                conn.execute(
                    text("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_handle_key")
                )
            conn.execute(
                text("CREATE INDEX IF NOT EXISTS ix_users_handle ON users (handle)")
            )
    except Exception:
        logger.exception("Could not relax the uniqueness of users.handle")


def init_db():
    Base.metadata.create_all(bind=engine)
    _relax_handle_uniqueness()
