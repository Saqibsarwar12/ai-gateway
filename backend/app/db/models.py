"""SQLAlchemy database models."""
from sqlalchemy import Column, String, Text, Boolean, Integer, Float, DateTime, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base


class Provider(Base):
    __tablename__ = "providers"

    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    base_url = Column(String(500), nullable=False)
    api_key = Column(String(500), nullable=False)
    enabled = Column(Boolean, default=True)
    status = Column(String(20), default="unknown")  # online, offline, degraded, unknown
    latency_ms = Column(Integer, default=0)
    cost_per_1k_input = Column(Float, default=0.0)
    cost_per_1k_output = Column(Float, default=0.0)
    daily_limit = Column(Integer, default=0)
    used_today = Column(Integer, default=0)
    priority = Column(Integer, default=1)
    tags = Column(JSON, default=list)
    headers = Column(JSON, default=dict)
    timeout_seconds = Column(Integer, default=60)
    retry_count = Column(Integer, default=3)
    models = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class RoutingRule(Base):
    __tablename__ = "routing_rules"

    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    strategy = Column(String(50), nullable=False)  # fallback, cost, latency, round_robin, weighted, priority
    provider_ids = Column(JSON, default=list)
    enabled = Column(Boolean, default=True)
    conditions = Column(JSON, default=dict)
    priority = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default="user")  # admin, staff, user, enterprise
    api_key = Column(String(64), unique=True, nullable=False)
    credits = Column(Integer, default=1000)
    requests_today = Column(Integer, default=0)
    rate_limit = Column(Integer, default=100)
    rate_window = Column(Integer, default=60)
    enabled = Column(Boolean, default=True)
    allowed_providers = Column(JSON, default=list)
    allowed_models = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    key = Column(String(64), unique=True, nullable=False)
    prefix = Column(String(10), default="agw_")
    rate_limit = Column(Integer, default=100)
    enabled = Column(Boolean, default=True)
    last_used = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RequestLog(Base):
    __tablename__ = "request_logs"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"))
    provider_id = Column(String(36), ForeignKey("providers.id"))
    model = Column(String(100), nullable=False)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    latency_ms = Column(Integer, default=0)
    status_code = Column(Integer, default=0)
    error = Column(Text)
    cost = Column(Float, default=0.0)
    cached = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Model(Base):
    __tablename__ = "models"

    id = Column(String(36), primary_key=True)
    provider_id = Column(String(36), ForeignKey("providers.id"), nullable=False)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False)
    enabled = Column(Boolean, default=True)
    hidden = Column(Boolean, default=False)
    cost_per_1k_input = Column(Float, default=0.0)
    cost_per_1k_output = Column(Float, default=0.0)
    max_tokens = Column(Integer, default=4096)
    supports_streaming = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint("provider_id", "slug"),)
