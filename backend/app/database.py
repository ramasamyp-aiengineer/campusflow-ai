from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.config import BASE_DIR, get_settings
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
            "quiz_lock_until": "VARCHAR(40) DEFAULT ''",
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


def _ensure_added_columns() -> None:
    if not settings.database_url.startswith("sqlite"):
        return
    added = {
        "learning_work_items": {
            "cosigned_by_id": "INTEGER REFERENCES users(id)",
            "cosigned_at": "VARCHAR(40)",
        },
        "signal_messages": {
            "sample": "BOOLEAN DEFAULT 0",
        },
    }
    with engine.begin() as connection:
        for table, columns in added.items():
            rows = connection.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
            if not rows:
                continue
            names = {row[1] for row in rows}
            for name, definition in columns.items():
                if name not in names:
                    connection.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")


def _upgrade_postgres() -> None:
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(BASE_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BASE_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(cfg, "head")


def init_db() -> None:
    from app.security.auth import ensure_demo_logins, purge_sessions
    from app.services.seed import seed_if_empty
    from app.services.signals import backfill_briefs, rescore_sentiment, seed_signals_if_empty

    if settings.database_url.startswith("sqlite"):
        Base.metadata.create_all(bind=engine)
        _ensure_signal_columns()
        _ensure_login_columns()
        _ensure_added_columns()
    else:
        _upgrade_postgres()
    with SessionLocal() as db:
        seed_if_empty(db)
        ensure_demo_logins(db)
        purge_sessions(db)
        seed_signals_if_empty(db)
        backfill_briefs(db)
        rescore_sentiment(db)
        db.commit()
