import secrets
import time

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import ModelCooldown, SchedulerLease

INSTANCE_ID = secrets.token_hex(8)


def model_is_resting(name: str) -> bool:
    with SessionLocal() as db:
        row = db.get(ModelCooldown, name)
        return row is not None and row.resting_until > time.time()


def rest_model(name: str, seconds: int) -> None:
    until = time.time() + seconds
    with SessionLocal() as db:
        row = db.get(ModelCooldown, name)
        if row is None:
            db.add(ModelCooldown(model_name=name, resting_until=until))
        else:
            row.resting_until = max(row.resting_until, until)
        db.commit()


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
