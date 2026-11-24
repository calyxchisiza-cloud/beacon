from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Application, Environment, User
from app.routers.auth import current_user
from app.schemas import (
    ApplicationIn,
    ApplicationOut,
    EnvironmentIn,
    EnvironmentOut,
    FlagConfigIn,
    FlagIn,
    MemberIn,
    OrgIn,
    OrgOut,
    SdkKeyIn,
    SdkKeyOut,
    SegmentIn,
)
from app.services import (
    add_member,
    create_application,
    create_environment,
    create_flag,
    create_org,
    create_sdk_key,
    create_segment,
    list_audit,
    list_flags,
    membership,
    update_flag_environment,
)

router = APIRouter(tags=["management"])


def _basis_points(percent: float | None) -> int | None:
    if percent is None:
        return None
    return int(round(percent * 100))


@router.post("/orgs", response_model=OrgOut, status_code=201)
def post_org(body: OrgIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> OrgOut:
    return create_org(db, user, body.name, body.slug)


@router.get("/orgs", response_model=list[OrgOut])
def get_orgs(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[OrgOut]:
    from app.models import Membership, Organisation

    rows = db.execute(
        select(Organisation)
        .join(Membership, Membership.organisation_id == Organisation.id)
        .where(Membership.user_id == user.id)
        .order_by(Organisation.slug)
    ).scalars()
    return list(rows)


@router.post("/orgs/{slug}/members", status_code=201)
def post_member(slug: str, body: MemberIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    row = add_member(db, user, slug, body.email, body.role)
    return {"id": row.id, "role": row.role}


@router.post("/orgs/{slug}/applications", response_model=ApplicationOut, status_code=201)
def post_application(
    slug: str, body: ApplicationIn, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> Application:
    return create_application(db, user, slug, body.key, body.name)


@router.get("/orgs/{slug}/applications", response_model=list[ApplicationOut])
def get_applications(slug: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[Application]:
    org, _ = membership(db, user, slug, "viewer")
    return list(db.scalars(select(Application).where(Application.organisation_id == org.id).order_by(Application.key)))


@router.post("/orgs/{slug}/applications/{app_key}/environments", response_model=EnvironmentOut, status_code=201)
def post_environment(
    slug: str,
    app_key: str,
    body: EnvironmentIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> Environment:
    return create_environment(db, user, slug, app_key, body.key, body.name)


@router.post("/orgs/{slug}/applications/{app_key}/environments/{env_key}/keys", response_model=SdkKeyOut, status_code=201)
def post_sdk_key(
    slug: str,
    app_key: str,
    env_key: str,
    body: SdkKeyIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> SdkKeyOut:
    row, token = create_sdk_key(db, user, slug, app_key, env_key, body.name)
    return SdkKeyOut(id=row.id, name=row.name, token=token)


@router.post("/orgs/{slug}/applications/{app_key}/segments", status_code=201)
def post_segment(
    slug: str, app_key: str, body: SegmentIn, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> dict:
    segment = create_segment(
        db, user, slug, app_key, body.key, body.name, [clause.model_dump() for clause in body.clauses]
    )
    return {"id": segment.id, "key": segment.key}


@router.post("/orgs/{slug}/applications/{app_key}/flags", status_code=201)
def post_flag(
    slug: str, app_key: str, body: FlagIn, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> dict:
    flag = create_flag(
        db,
        user,
        slug,
        app_key,
        body.key,
        body.name,
        body.description,
        body.variations,
        body.off_variation,
        body.fallthrough_variation,
    )
    return {"id": flag.id, "key": flag.key, "variations": flag.variations}


@router.get("/orgs/{slug}/applications/{app_key}/flags")
def get_flags(slug: str, app_key: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[dict]:
    return [{"id": flag.id, "key": flag.key, "name": flag.name, "variations": flag.variations} for flag in list_flags(db, user, slug, app_key)]


@router.put("/orgs/{slug}/applications/{app_key}/flags/{flag_key}/environments/{env_key}")
def put_flag_environment(
    slug: str,
    app_key: str,
    flag_key: str,
    env_key: str,
    body: FlagConfigIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    row = update_flag_environment(
        db,
        user,
        slug,
        app_key,
        flag_key,
        env_key,
        body.enabled,
        body.off_variation,
        body.fallthrough_variation,
        _basis_points(body.rollout_percent),
        body.salt,
        [rule.model_dump() for rule in body.rules],
    )
    return {"enabled": row.enabled, "rollout_basis_points": row.rollout_basis_points}


@router.get("/orgs/{slug}/audit")
def get_audit(slug: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[dict]:
    return [
        {"action": row.action, "resource": row.resource, "detail": row.detail, "created_at": row.created_at.isoformat()}
        for row in list_audit(db, user, slug)
    ]
