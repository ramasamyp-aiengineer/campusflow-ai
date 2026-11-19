import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.limiter import limiter
from app.models import User
from app.routers.api import bearer_token
from app.schemas import DemoSwitchIn, LoginIn, LoginOut, RegisterIn, SessionUser
from app.security.auth import DEMO_EMAILS, PERSONA_FOR_ROLE, authenticate, end_session, hash_password, session_for, start_session
from app.services.board import audit

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

WRONG_LOGIN = "That email and password do not match an account."


def _user_out(user: User) -> SessionUser:
    return SessionUser(
        id=user.id,
        name=user.name,
        email=user.email or "",
        role=user.role,
        persona=PERSONA_FOR_ROLE[user.role],
        avatar_initials=user.avatar_initials,
        program=user.program,
    )


def _session_user(db: Session, authorization: str) -> tuple[str, User]:
    token = bearer_token(authorization)
    session = session_for(db, token) if token else None
    user = db.get(User, session.user_id) if session else None
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to continue")
    return token, user


def _initials(name: str) -> str:
    parts = [part for part in name.split() if part]
    letters = "".join(part[0] for part in parts[:2]) or name[:2]
    return letters.upper()[:4]


@router.post("/register", response_model=LoginOut)
@limiter.limit("5/minute")
def register(request: Request, response: Response, body: RegisterIn, db: Session = Depends(get_db)) -> LoginOut:
    email = body.email.strip().lower()
    if "@" not in email or email.startswith("@") or email.endswith("@") or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=400, detail="Enter a campus email address.")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="An account with that email already exists.")
    user = User(
        name=body.name.strip(),
        role="STUDENT",
        department="CSE",
        semester=5,
        avatar_initials=_initials(body.name),
        anon_token=secrets.token_hex(8),
        cgpa=0,
        velocity_drop_pct=0,
        is_persona=False,
        program="B.Tech CSE",
        email=email,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    db.flush()
    token, expires_at = start_session(db, user)
    audit(db, user, "auth.register", "student account created")
    db.commit()
    return LoginOut(token=token, expires_at=expires_at, user=_user_out(user))


@router.post("/login", response_model=LoginOut)
@limiter.limit("20/minute")
def login(request: Request, response: Response, body: LoginIn, db: Session = Depends(get_db)) -> LoginOut:
    user = authenticate(db, body.email, body.password)
    if user is None or user.role not in PERSONA_FOR_ROLE:
        known = db.query(User).filter(User.email == body.email.strip().lower()).first()
        if known is not None:
            audit(db, known, "auth.failed", "wrong password")
            db.commit()
        raise HTTPException(status_code=401, detail=WRONG_LOGIN)
    token, expires_at = start_session(db, user)
    audit(db, user, "auth.login", "signed in")
    db.commit()
    return LoginOut(token=token, expires_at=expires_at, user=_user_out(user))


@router.get("/me", response_model=SessionUser)
def me(authorization: str = Header(default=""), db: Session = Depends(get_db)) -> SessionUser:
    _, user = _session_user(db, authorization)
    return _user_out(user)


@router.post("/logout", status_code=204)
def logout(authorization: str = Header(default=""), db: Session = Depends(get_db)) -> Response:
    token, user = _session_user(db, authorization)
    end_session(db, token)
    audit(db, user, "auth.logout", "signed out")
    db.commit()
    return Response(status_code=204)


def _demo_email_for_persona(persona: str) -> str | None:
    mapping = {"student": "STU_8921", "faculty": "FAC_1044", "tpo": "TPO_017"}
    token = mapping.get(persona.strip().lower())
    return DEMO_EMAILS.get(token) if token else None


@router.post("/demo-switch", response_model=LoginOut)
@limiter.limit("20/minute")
def demo_switch(request: Request, response: Response, body: DemoSwitchIn, db: Session = Depends(get_db)) -> LoginOut:
    """Hackathon persona switch. Password stays server-side; never embed it in NEXT_PUBLIC_*. """
    settings = get_settings()
    if not settings.demo_password.strip():
        raise HTTPException(status_code=404, detail="Demo switch is disabled")
    persona = body.persona.strip().lower()
    email = _demo_email_for_persona(persona)
    if email is None:
        raise HTTPException(status_code=400, detail="Unknown demo persona")
    user = authenticate(db, email, settings.demo_password)
    if user is None or user.role not in PERSONA_FOR_ROLE:
        raise HTTPException(status_code=401, detail=WRONG_LOGIN)
    token, expires_at = start_session(db, user)
    audit(db, user, "auth.demo_switch", f"persona={persona}")
    db.commit()
    return LoginOut(token=token, expires_at=expires_at, user=_user_out(user))
