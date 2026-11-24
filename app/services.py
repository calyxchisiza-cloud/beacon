import re
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cache import cache
from app.models import (
    Application,
    AuditLog,
    Environment,
    EvaluationEvent,
    FeatureFlag,
    FlagEnvironment,
    Membership,
    Organisation,
    SdkKey,
    Segment,
    User,
)
from app.security import hash_password, hash_token, new_sdk_token, verify_password

KEY = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
ROLES = {"viewer": 0, "developer": 1, "admin": 2, "owner": 3}


def bad(status: int, detail: str) -> HTTPException:
    return HTTPException(status_code=status, detail=detail)


def require_key(value: str, label: str) -> str:
    if not KEY.fullmatch(value or ""):
        raise bad(400, f"{label} is not valid")
    return value


def register_user(db: Session, email: str, name: str, password: str) -> User:
    email = email.strip().lower()
    if "@" not in email or len(password) < 8 or not name.strip():
        raise bad(400, "account is not valid")
    if db.scalar(select(User).where(User.email == email)):
        raise bad(409, "email is already registered")
    user = User(email=email, name=name.strip(), password_hash=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None or not verify_password(password, user.password_hash):
        raise bad(401, "email or password is wrong")
    return user


def membership(db: Session, user: User, slug: str, minimum: str = "viewer") -> tuple[Organisation, Membership]:
    org = db.scalar(select(Organisation).where(Organisation.slug == slug))
    if org is None:
        raise bad(404, "organisation not found")
    row = db.scalar(
        select(Membership).where(Membership.user_id == user.id, Membership.organisation_id == org.id)
    )
    if row is None or ROLES[row.role] < ROLES[minimum]:
        raise bad(404, "organisation not found")
    return org, row


def create_org(db: Session, user: User, name: str, slug: str) -> Organisation:
    slug = require_key(slug, "slug")
    if not name.strip():
        raise bad(400, "name is required")
    if db.scalar(select(Organisation).where(Organisation.slug == slug)):
        raise bad(409, "slug is already used")
    org = Organisation(name=name.strip(), slug=slug)
    db.add(org)
    db.flush()
    db.add(Membership(user_id=user.id, organisation_id=org.id, role="owner"))
    _audit(db, org.id, user.id, "org.create", slug, {"name": org.name})
    db.commit()
    db.refresh(org)
    return org


def add_member(db: Session, actor: User, slug: str, email: str, role: str) -> Membership:
    if role not in ROLES or role == "owner":
        raise bad(400, "role is not valid")
    org, _ = membership(db, actor, slug, "admin")
    person = db.scalar(select(User).where(User.email == email.strip().lower()))
    if person is None:
        raise bad(404, "user not found")
    existing = db.scalar(
        select(Membership).where(Membership.user_id == person.id, Membership.organisation_id == org.id)
    )
    if existing:
        raise bad(409, "user is already a member")
    row = Membership(user_id=person.id, organisation_id=org.id, role=role)
    db.add(row)
    _audit(db, org.id, actor.id, "member.add", email, {"role": role})
    db.commit()
    db.refresh(row)
    return row


def create_application(db: Session, user: User, slug: str, key: str, name: str) -> Application:
    org, _ = membership(db, user, slug, "developer")
    key = require_key(key, "key")
    if not name.strip():
        raise bad(400, "name is required")
    if db.scalar(select(Application).where(Application.organisation_id == org.id, Application.key == key)):
        raise bad(409, "application already exists")
    app = Application(organisation_id=org.id, key=key, name=name.strip())
    db.add(app)
    _audit(db, org.id, user.id, "application.create", key, {"name": app.name})
    db.commit()
    db.refresh(app)
    return app


def _application(db: Session, user: User, slug: str, key: str, minimum: str) -> tuple[Organisation, Application]:
    org, _ = membership(db, user, slug, minimum)
    app = db.scalar(select(Application).where(Application.organisation_id == org.id, Application.key == key))
    if app is None:
        raise bad(404, "application not found")
    return org, app


def create_environment(db: Session, user: User, slug: str, app_key: str, key: str, name: str) -> Environment:
    org, app = _application(db, user, slug, app_key, "developer")
    key = require_key(key, "key")
    if db.scalar(select(Environment).where(Environment.application_id == app.id, Environment.key == key)):
        raise bad(409, "environment already exists")
    env = Environment(application_id=app.id, key=key, name=name.strip() or key)
    db.add(env)
    db.flush()
    for flag in db.scalars(select(FeatureFlag).where(FeatureFlag.application_id == app.id)):
        db.add(_blank_config(flag, env.id))
    _audit(db, org.id, user.id, "environment.create", f"{app_key}/{key}", {})
    db.commit()
    db.refresh(env)
    return env


def create_sdk_key(db: Session, user: User, slug: str, app_key: str, env_key: str, name: str) -> tuple[SdkKey, str]:
    org, app = _application(db, user, slug, app_key, "developer")
    env = _environment(db, app, env_key)
    token = new_sdk_token()
    row = SdkKey(environment_id=env.id, name=name.strip() or "sdk", token_hash=hash_token(token))
    db.add(row)
    _audit(db, org.id, user.id, "sdk_key.create", f"{app_key}/{env_key}", {"name": row.name})
    db.commit()
    db.refresh(row)
    return row, token


def create_segment(db: Session, user: User, slug: str, app_key: str, key: str, name: str, clauses: list) -> Segment:
    org, app = _application(db, user, slug, app_key, "developer")
    key = require_key(key, "key")
    _check_clauses(clauses)
    if db.scalar(select(Segment).where(Segment.application_id == app.id, Segment.key == key)):
        raise bad(409, "segment already exists")
    segment = Segment(application_id=app.id, key=key, name=name.strip() or key, clauses=clauses)
    db.add(segment)
    _audit(db, org.id, user.id, "segment.create", f"{app_key}/{key}", {})
    _drop_app_cache(db, app.id)
    db.commit()
    db.refresh(segment)
    return segment


def create_flag(
    db: Session,
    user: User,
    slug: str,
    app_key: str,
    key: str,
    name: str,
    description: str,
    variations: dict[str, Any],
    off_variation: str,
    fallthrough_variation: str,
) -> FeatureFlag:
    org, app = _application(db, user, slug, app_key, "developer")
    key = require_key(key, "key")
    if not variations or off_variation not in variations or fallthrough_variation not in variations:
        raise bad(400, "variations are not valid")
    if db.scalar(select(FeatureFlag).where(FeatureFlag.application_id == app.id, FeatureFlag.key == key)):
        raise bad(409, "flag already exists")
    flag = FeatureFlag(
        application_id=app.id,
        key=key,
        name=name.strip() or key,
        description=description,
        variations=variations,
    )
    db.add(flag)
    db.flush()
    for env in db.scalars(select(Environment).where(Environment.application_id == app.id)):
        db.add(_blank_config(flag, env.id, off_variation, fallthrough_variation))
    _audit(db, org.id, user.id, "flag.create", f"{app_key}/{key}", {})
    db.commit()
    db.refresh(flag)
    return flag


def update_flag_environment(
    db: Session,
    user: User,
    slug: str,
    app_key: str,
    flag_key: str,
    env_key: str,
    enabled: bool,
    off_variation: str,
    fallthrough_variation: str,
    rollout_basis_points: int | None,
    salt: str,
    rules: list,
) -> FlagEnvironment:
    org, app = _application(db, user, slug, app_key, "developer")
    flag = _flag(db, app, flag_key)
    env = _environment(db, app, env_key)
    if off_variation not in flag.variations or fallthrough_variation not in flag.variations:
        raise bad(400, "variation is not valid")
    if rollout_basis_points is not None and not 0 <= rollout_basis_points <= 10000:
        raise bad(400, "rollout is not valid")
    _check_rules(rules, flag.variations)
    row = db.scalar(
        select(FlagEnvironment).where(
            FlagEnvironment.flag_id == flag.id, FlagEnvironment.environment_id == env.id
        )
    )
    if row is None:
        row = _blank_config(flag, env.id)
        db.add(row)
    row.enabled = enabled
    row.off_variation = off_variation
    row.fallthrough_variation = fallthrough_variation
    row.rollout_basis_points = rollout_basis_points
    row.salt = salt or row.salt or flag.key
    row.rules = rules
    _audit(db, org.id, user.id, "flag.update", f"{app_key}/{flag_key}/{env_key}", {"enabled": enabled})
    db.commit()
    cache.delete(_cache_key(env.id))
    db.refresh(row)
    return row


def list_flags(db: Session, user: User, slug: str, app_key: str) -> list[FeatureFlag]:
    _, app = _application(db, user, slug, app_key, "viewer")
    return list(db.scalars(select(FeatureFlag).where(FeatureFlag.application_id == app.id).order_by(FeatureFlag.key)))


def list_audit(db: Session, user: User, slug: str) -> list[AuditLog]:
    org, _ = membership(db, user, slug, "viewer")
    return list(
        db.scalars(
            select(AuditLog).where(AuditLog.organisation_id == org.id).order_by(AuditLog.created_at.desc()).limit(100)
        )
    )


def environment_for_token(db: Session, token: str) -> Environment:
    row = db.scalar(select(SdkKey).where(SdkKey.token_hash == hash_token(token)))
    if row is None:
        raise bad(401, "sdk key is not valid")
    env = db.get(Environment, row.environment_id)
    if env is None:
        raise bad(401, "sdk key is not valid")
    return env


def snapshot_for(db: Session, environment_id: str) -> dict:
    cached = cache.get(_cache_key(environment_id))
    if cached is not None:
        return cached
    built = _build_snapshot(db, environment_id)
    cache.set(_cache_key(environment_id), built)
    return built


def record_events(db: Session, environment_id: str, events: list[dict]) -> int:
    if len(events) > 100:
        raise bad(400, "too many events")
    for event in events:
        db.add(
            EvaluationEvent(
                environment_id=environment_id,
                flag_key=str(event["flag"])[:80],
                user_key=str(event["user_key"])[:200],
                variation=str(event["variation"])[:80],
                reason=str(event.get("reason") or "")[:40],
            )
        )
    db.commit()
    return len(events)


def _build_snapshot(db: Session, environment_id: str) -> dict:
    env = db.get(Environment, environment_id)
    if env is None:
        raise bad(404, "environment not found")
    segments = {
        segment.key: {"clauses": segment.clauses}
        for segment in db.scalars(select(Segment).where(Segment.application_id == env.application_id))
    }
    flags = []
    rows = db.execute(
        select(FeatureFlag, FlagEnvironment)
        .join(FlagEnvironment, FlagEnvironment.flag_id == FeatureFlag.id)
        .where(FlagEnvironment.environment_id == environment_id)
        .order_by(FeatureFlag.key)
    )
    for flag, config in rows:
        flags.append(
            {
                "key": flag.key,
                "enabled": config.enabled,
                "off": config.off_variation,
                "fallthrough": config.fallthrough_variation,
                "salt": config.salt,
                "rollout": config.rollout_basis_points,
                "rules": config.rules or [],
                "variations": flag.variations,
            }
        )
    return {"segments": segments, "flags": flags}


def _blank_config(
    flag: FeatureFlag,
    environment_id: str,
    off_variation: str | None = None,
    fallthrough: str | None = None,
) -> FlagEnvironment:
    first = off_variation or next(iter(flag.variations))
    return FlagEnvironment(
        flag_id=flag.id,
        environment_id=environment_id,
        enabled=False,
        off_variation=first,
        fallthrough_variation=fallthrough or first,
        rollout_basis_points=None,
        salt=flag.key,
        rules=[],
    )


def _environment(db: Session, app: Application, key: str) -> Environment:
    env = db.scalar(select(Environment).where(Environment.application_id == app.id, Environment.key == key))
    if env is None:
        raise bad(404, "environment not found")
    return env


def _flag(db: Session, app: Application, key: str) -> FeatureFlag:
    flag = db.scalar(select(FeatureFlag).where(FeatureFlag.application_id == app.id, FeatureFlag.key == key))
    if flag is None:
        raise bad(404, "flag not found")
    return flag


def _check_clauses(clauses: list) -> None:
    for clause in clauses:
        if clause.get("op") not in {"eq", "in", "contains", "starts_with", "ends_with", "gt", "lt"}:
            raise bad(400, "clause is not valid")
        if not clause.get("attribute") or not isinstance(clause.get("values"), list):
            raise bad(400, "clause is not valid")


def _check_rules(rules: list, variations: dict) -> None:
    for rule in rules:
        if rule.get("variation") not in variations:
            raise bad(400, "variation is not valid")
        rollout = rule.get("rollout")
        if rollout is not None and not isinstance(rollout, int):
            raise bad(400, "rollout is not valid")
        if isinstance(rollout, int) and not 0 <= rollout <= 10000:
            raise bad(400, "rollout is not valid")
        _check_clauses(rule.get("clauses") or [])


def _audit(db: Session, org_id: str, actor_id: str | None, action: str, resource: str, detail: dict) -> None:
    db.add(AuditLog(organisation_id=org_id, actor_id=actor_id, action=action, resource=resource, detail=detail))


def _drop_app_cache(db: Session, application_id: str) -> None:
    for env in db.scalars(select(Environment).where(Environment.application_id == application_id)):
        cache.delete(_cache_key(env.id))


def _cache_key(environment_id: str) -> str:
    return f"beacon:env:{environment_id}"
