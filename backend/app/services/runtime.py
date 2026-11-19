import secrets
import time

from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.database import SessionLocal, engine
from app.models import ModelCooldown, SchedulerLease

INSTANCE_ID = secrets.token_hex(8)


def _cooldown_session() -> Session:
    db = SessionLocal()
    if engine.dialect.name == "sqlite":
        db.connection().exec_driver_sql("PRAGMA busy_timeout=250")
    return db


def model_is_resting(name: str) -> bool:
    try:
        with _cooldown_session() as db:
            row = db.get(ModelCooldown, name)
            return row is not None and row.resting_until > time.time()
    except OperationalError:
        return False


def rest_model(name: str, seconds: int) -> None:
    """Best-effort cooldown. A lock held by the caller must not fail the request."""
    until = time.time() + seconds
    try:
        with _cooldown_session() as db:
            row = db.get(ModelCooldown, name)
            if row is None:
                db.add(ModelCooldown(model_name=name, resting_until=until))
            else:
                row.resting_until = max(row.resting_until, until)
            db.commit()
    except OperationalError:
        return


def acquire_lease(db: Session, name: str, seconds: int, owner: str | None = None) -> bool:
    """Take or renew a lease. A different live owner is left alone."""
    holder = owner or INSTANCE_ID
    now = time.time()
    until = now + seconds
    row = db.get(SchedulerLease, name)
    if row is None:
        db.add(SchedulerLease(name=name, owner=holder, expires_at=until))
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            return False
        return True
    if row.expires_at > now and row.owner != holder:
        return False
    row.owner = holder
    row.expires_at = until
    db.flush()
    return True
