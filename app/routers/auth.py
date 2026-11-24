import secrets

import jwt
from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import User
from app.schemas import OIDCIn, RegisterIn, TokenOut, UserOut
from app.security import create_access_token, read_access_token
from app.services import authenticate, bad, register_user

router = APIRouter(prefix="/auth", tags=["auth"])
bearer = HTTPBearer(auto_error=False)


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise bad(401, "login is required")
    try:
        user_id = read_access_token(credentials.credentials)
    except jwt.PyJWTError:
        raise bad(401, "login is required") from None
    user = db.get(User, user_id)
    if user is None:
        raise bad(401, "login is required")
    return user


@router.post("/register", response_model=TokenOut, status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)) -> TokenOut:
    user = register_user(db, body.email, body.name, body.password)
    return TokenOut(access_token=create_access_token(user.id))


@router.post("/token", response_model=TokenOut)
def token(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> TokenOut:
    user = authenticate(db, form.username, form.password)
    return TokenOut(access_token=create_access_token(user.id))


@router.post("/oidc", response_model=TokenOut)
def oidc(body: OIDCIn, db: Session = Depends(get_db)) -> TokenOut:
    settings = get_settings()
    if not settings.oidc_issuer or not settings.oidc_jwks_url or not settings.oidc_audience:
        raise bad(503, "oidc is not configured")
    try:
        signing_key = jwt.PyJWKClient(settings.oidc_jwks_url).get_signing_key_from_jwt(body.id_token)
        payload = jwt.decode(
            body.id_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.oidc_audience,
            issuer=settings.oidc_issuer,
        )
    except jwt.PyJWTError:
        raise bad(401, "oidc token is not valid") from None
    email = str(payload.get("email") or "").strip().lower()
    if "@" not in email:
        raise bad(400, "oidc token has no email")
    from sqlalchemy import select

    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = register_user(db, email, str(payload.get("name") or email), secrets.token_urlsafe(24))
    return TokenOut(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)) -> User:
    return user
