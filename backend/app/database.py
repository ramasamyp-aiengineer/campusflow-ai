from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.models import Base

settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@event.listens_for(engine, "connect")
def _sqlite_pragmas(dbapi_connection, _connection_record) -> None:
    if not settings.database_url.startswith("sqlite"):
        return
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=10000")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _ensure_signal_columns() -> None:
    if not settings.database_url.startswith("sqlite"):
        return
    with engine.begin() as connection:
        rows = connection.exec_driver_sql("PRAGMA table_info(signal_messages)").fetchall()
        if not rows:
            return
        names = {row[1] for row in rows}
        columns = {
            "brief": "TEXT DEFAULT ''",
            "brief_source": "VARCHAR(20) DEFAULT 'local'",
            "sources_json": "TEXT DEFAULT '[]'",
            "task_lwi_id": "INTEGER REFERENCES learning_work_items(id)",
            "explainer_json": "TEXT DEFAULT ''",
            "quiz_passed": "BOOLEAN DEFAULT 0",
        }
        for name, definition in columns.items():
            if name not in names:
                connection.exec_driver_sql(f"ALTER TABLE signal_messages ADD COLUMN {name} {definition}")


def _ensure_login_columns() -> None:
    if not settings.database_url.startswith("sqlite"):
        return
    with engine.begin() as connection:
        names = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(users)").fetchall()}
        if not names:
            return
        if "email" not in names:
            connection.exec_driver_sql("ALTER TABLE users ADD COLUMN email VARCHAR(160)")
        if "password_hash" not in names:
            connection.exec_driver_sql("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255) DEFAULT ''")
        connection.exec_driver_sql("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email)")


def init_db() -> None:
    from app.security.auth import ensure_demo_logins
    from app.services.seed import seed_if_empty
    from app.services.signals import backfill_briefs, rescore_sentiment, seed_signals_if_empty

    Base.metadata.create_all(bind=engine)
    _ensure_signal_columns()
    _ensure_login_columns()
    with SessionLocal() as db:
        seed_if_empty(db)
        ensure_demo_logins(db)
        seed_signals_if_empty(db)
        backfill_briefs(db)
        rescore_sentiment(db)
        db.commit()
