import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt

from app.config import get_settings

PBKDF2_ROUNDS = 60_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), PBKDF2_ROUNDS)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    salt, digest = stored.split("$", 1)
    check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), PBKDF2_ROUNDS)
    return hmac.compare_digest(check.hex(), digest)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_sdk_token() -> str:
    return "bk_" + secrets.token_urlsafe(32)


def create_access_token(user_id: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {"sub": user_id, "iat": int(now.timestamp()), "exp": now + timedelta(seconds=settings.jwt_ttl_seconds)}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def read_access_token(token: str) -> str:
    settings = get_settings()
    payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    subject = payload.get("sub")
    if not subject:
        raise jwt.InvalidTokenError("missing subject")
    return str(subject)
