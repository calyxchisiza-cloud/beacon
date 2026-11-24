from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.db import get_db
from beacon_core.eval import evaluate_all, evaluate_flag
from app.schemas import EvaluateIn, EventsIn
from app.services import bad, environment_for_token, record_events, snapshot_for

router = APIRouter(prefix="/sdk/v1", tags=["sdk"])


def _token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise bad(401, "sdk key is required")
    return authorization.split(" ", 1)[1].strip()


@router.get("/flags")
def flags(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> dict:
    env = environment_for_token(db, _token(authorization))
    return snapshot_for(db, env.id)


@router.post("/evaluate")
def evaluate(body: EvaluateIn, authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> dict:
    env = environment_for_token(db, _token(authorization))
    snapshot = snapshot_for(db, env.id)
    user = body.user.model_dump()
    if body.flag:
        flag = next((item for item in snapshot["flags"] if item["key"] == body.flag), None)
        if flag is None:
            raise bad(404, "flag not found")
        return evaluate_flag(flag, user, snapshot.get("segments") or {})
    return {"flags": evaluate_all(snapshot, user)}


@router.post("/events", status_code=202)
def events(body: EventsIn, authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> dict:
    env = environment_for_token(db, _token(authorization))
    count = record_events(db, env.id, [event.model_dump() for event in body.events])
    return {"accepted": count}
