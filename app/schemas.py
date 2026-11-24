from typing import Any

from pydantic import BaseModel, Field


class RegisterIn(BaseModel):
    email: str
    name: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class OIDCIn(BaseModel):
    id_token: str


class UserOut(BaseModel):
    id: str
    email: str
    name: str


class OrgIn(BaseModel):
    name: str
    slug: str


class OrgOut(BaseModel):
    id: str
    name: str
    slug: str


class MemberIn(BaseModel):
    email: str
    role: str


class ApplicationIn(BaseModel):
    key: str
    name: str


class ApplicationOut(BaseModel):
    id: str
    key: str
    name: str


class EnvironmentIn(BaseModel):
    key: str
    name: str = ""


class EnvironmentOut(BaseModel):
    id: str
    key: str
    name: str


class SdkKeyIn(BaseModel):
    name: str = "sdk"


class SdkKeyOut(BaseModel):
    id: str
    name: str
    token: str


class ClauseIn(BaseModel):
    attribute: str
    op: str
    values: list[Any]


class SegmentIn(BaseModel):
    key: str
    name: str = ""
    clauses: list[ClauseIn] = Field(default_factory=list)


class FlagIn(BaseModel):
    key: str
    name: str = ""
    description: str = ""
    variations: dict[str, Any]
    off_variation: str
    fallthrough_variation: str


class RuleIn(BaseModel):
    id: str = ""
    clauses: list[ClauseIn] = Field(default_factory=list)
    variation: str
    rollout: int | None = None


class FlagConfigIn(BaseModel):
    enabled: bool
    off_variation: str
    fallthrough_variation: str
    rollout_percent: float | None = None
    salt: str = ""
    rules: list[RuleIn] = Field(default_factory=list)


class UserContext(BaseModel):
    key: str
    attributes: dict[str, Any] = Field(default_factory=dict)


class EvaluateIn(BaseModel):
    user: UserContext
    flag: str | None = None


class EventIn(BaseModel):
    flag: str
    user_key: str
    variation: str
    reason: str = ""


class EventsIn(BaseModel):
    events: list[EventIn]
