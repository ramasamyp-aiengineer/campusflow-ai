import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import AuthSession, User, utcnow

PERSONA_FOR_ROLE = {"STUDENT": "student", "FACULTY": "faculty", "TPO": "tpo"}
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2**14, 8, 1
DEMO_EMAILS = {
    "STU_8921": "arjun@campusflow.edu",
    "FAC_1044": "meenakshi@campusflow.edu",
    "TPO_017": "placement@campusflow.edu",
}


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=32)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt, expected = stored.split("$")
        if scheme != "scrypt":
            return False
        digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p), dklen=32)
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest.hex(), expected)


_DUMMY_HASH = hash_password(secrets.token_urlsafe(12))


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def authenticate(db: Session, email: str, password: str) -> User | None:
    user = db.query(User).filter(User.email == email.strip().lower()).first()
    if user is None or not user.password_hash:
        verify_password(password, _DUMMY_HASH)
        return None
    return user if verify_password(password, user.password_hash) else None


def start_session(db: Session, user: User) -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    expires = (datetime.now(timezone.utc) + timedelta(hours=get_settings().session_hours)).replace(microsecond=0).isoformat()
    db.add(AuthSession(token_hash=_token_hash(token), user_id=user.id, expires_at=expires))
    return token, expires


def session_for(db: Session, token: str) -> AuthSession | None:
    row = db.query(AuthSession).filter(AuthSession.token_hash == _token_hash(token)).first()
    if row is None or row.revoked_at or row.expires_at <= utcnow():
        return None
    return row


def end_session(db: Session, token: str) -> None:
    row = session_for(db, token)
    if row is not None:
        row.revoked_at = utcnow()


def ensure_demo_logins(db: Session) -> None:
    password = get_settings().demo_password
    if not password:
        return
    for anon_token, email in DEMO_EMAILS.items():
        user = db.query(User).filter(User.anon_token == anon_token).first()
        if user is None or user.password_hash:
            continue
        user.email = email
        user.password_hash = hash_password(password)
