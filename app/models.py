import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db import Base


def new_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Organisation(Base):
    __tablename__ = "organisations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("user_id", "organisation_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    organisation_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"), index=True)
    role: Mapped[str] = mapped_column(String(20))


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("organisation_id", "key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organisation_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"), index=True)
    key: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Environment(Base):
    __tablename__ = "environments"
    __table_args__ = (UniqueConstraint("application_id", "key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    application_id: Mapped[str] = mapped_column(ForeignKey("applications.id"), index=True)
    key: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(200))


class SdkKey(Base):
    __tablename__ = "sdk_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    environment_id: Mapped[str] = mapped_column(ForeignKey("environments.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class FeatureFlag(Base):
    __tablename__ = "feature_flags"
    __table_args__ = (UniqueConstraint("application_id", "key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    application_id: Mapped[str] = mapped_column(ForeignKey("applications.id"), index=True)
    key: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    variations: Mapped[dict] = mapped_column(JSON)


class FlagEnvironment(Base):
    __tablename__ = "flag_environments"
    __table_args__ = (UniqueConstraint("flag_id", "environment_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    flag_id: Mapped[str] = mapped_column(ForeignKey("feature_flags.id"), index=True)
    environment_id: Mapped[str] = mapped_column(ForeignKey("environments.id"), index=True)
    enabled: Mapped[bool] = mapped_column(default=False)
    off_variation: Mapped[str] = mapped_column(String(80))
    fallthrough_variation: Mapped[str] = mapped_column(String(80))
    rollout_basis_points: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salt: Mapped[str] = mapped_column(String(80), default="")
    rules: Mapped[list] = mapped_column(JSON, default=list)


class Segment(Base):
    __tablename__ = "segments"
    __table_args__ = (UniqueConstraint("application_id", "key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    application_id: Mapped[str] = mapped_column(ForeignKey("applications.id"), index=True)
    key: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(200))
    clauses: Mapped[list] = mapped_column(JSON, default=list)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_org_time", "organisation_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organisation_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"), index=True)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(80))
    resource: Mapped[str] = mapped_column(String(200))
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class EvaluationEvent(Base):
    __tablename__ = "evaluation_events"
    __table_args__ = (Index("ix_events_env_time", "environment_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    environment_id: Mapped[str] = mapped_column(ForeignKey("environments.id"), index=True)
    flag_key: Mapped[str] = mapped_column(String(80))
    user_key: Mapped[str] = mapped_column(String(200))
    variation: Mapped[str] = mapped_column(String(80))
    reason: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
