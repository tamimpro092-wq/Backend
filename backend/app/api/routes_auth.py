from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlmodel import Session, select

from ..auth import create_token, decode_token, hash_password, verify_password
from ..db import get_session
from ..models import User
from ..schemas import LoginRequest, LoginResponse, SignupRequest, UserOut

# ✅ IMPORTANT: your project uses /api prefix in every router
router = APIRouter(prefix="/api/auth", tags=["auth"])


def _get_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    if not authorization.lower().startswith("bearer "):
        return None
    return authorization.split(" ", 1)[1].strip()


@router.post("/signup", response_model=UserOut)
def signup(payload: SignupRequest, session: Session = Depends(get_session)) -> UserOut:
    username = payload.username.strip()
    if not username or not payload.password:
        raise HTTPException(status_code=400, detail="Username and password required")

    existing = session.exec(select(User).where(User.username == username)).first()
    if existing:
        raise HTTPException(status_code=409, detail="Username already exists")

    user = User(username=username, password_hash=hash_password(payload.password))
    session.add(user)
    session.commit()
    session.refresh(user)

    return UserOut(id=user.id, username=user.username)


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, session: Session = Depends(get_session)) -> LoginResponse:
    username = payload.username.strip()
    user = session.exec(select(User).where(User.username == username)).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_token(subject=user.username)
    return LoginResponse(access_token=token, token_type="bearer", user=UserOut(id=user.id, username=user.username))


@router.get("/me", response_model=UserOut)
def me(
    session: Session = Depends(get_session),
    authorization: str | None = Header(default=None),
) -> UserOut:
    token = _get_bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token")

    data = decode_token(token)
    if not data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = session.exec(select(User).where(User.username == data.sub)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return UserOut(id=user.id, username=user.username)
