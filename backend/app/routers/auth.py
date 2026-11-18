from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.limiter import limiter
from app.models import User
from app.routers.api import bearer_token
from app.schemas import LoginIn, LoginOut, SessionUser
from app.security.auth import PERSONA_FOR_ROLE, authenticate, end_session, session_for, start_session
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


@router.post("/login", response_model=LoginOut)
@limiter.limit("5/minute")
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
