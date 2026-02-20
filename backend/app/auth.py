from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .settings import settings


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def hash_password(password: str) -> str:
    """
    Simple salted hash using HMAC-SHA256 with AUTH_SECRET as key.
    (Keeps dependencies minimal. If you want bcrypt later, we can swap it.)
    """
    key = settings.AUTH_SECRET.encode("utf-8")
    return hmac.new(key, password.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hmac.compare_digest(hash_password(password), password_hash)


@dataclass
class TokenData:
    sub: str
    exp: int


def create_token(subject: str, expires_minutes: Optional[int] = None) -> str:
    if expires_minutes is None:
        expires_minutes = settings.AUTH_TOKEN_EXPIRE_MINUTES

    exp = int(time.time()) + int(expires_minutes) * 60
    payload = {"sub": subject, "exp": exp}
    payload_bytes = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    sig = hmac.new(settings.AUTH_SECRET.encode("utf-8"), payload_bytes, hashlib.sha256).digest()

    return f"{_b64url_encode(payload_bytes)}.{_b64url_encode(sig)}"


def decode_token(token: str) -> Optional[TokenData]:
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None

        payload_b64, sig_b64 = parts
        payload_bytes = _b64url_decode(payload_b64)
        sig = _b64url_decode(sig_b64)

        expected_sig = hmac.new(settings.AUTH_SECRET.encode("utf-8"), payload_bytes, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expected_sig):
            return None

        payload: Dict[str, Any] = json.loads(payload_bytes.decode("utf-8"))
        sub = str(payload.get("sub", ""))
        exp = int(payload.get("exp", 0))

        if not sub:
            return None
        if exp <= int(time.time()):
            return None

        return TokenData(sub=sub, exp=exp)
    except Exception:
        return None
