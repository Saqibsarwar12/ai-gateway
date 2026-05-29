"""SQLAlchemy database models for AI Gateway."""
from sqlalchemy import Column, String, Text, Boolean, Integer, Float, DateTime, JSON, Index
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime


class Base(DeclarativeBase):
    pass


class Provider(Base):
    __tablename__ = "providers"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    provider_type = Column(String, nullable=False)  # openai | anthropic | gemini | deepseek | ollama | custom
    base_url = Column(String, nullable=False)
    api_key = Column(String)
    enabled = Column(Boolean, default=True)
    priority = Column(Integer, default=100)  # Lower = higher priority
    max_rpm = Column(Integer, default=1000)
    max_tpm = Column(Integer, default=100000)
    current_rpm = Column(Integer, default=0)
    current_tpm = Column(Integer, default=0)
    avg_latency_ms = Column(Float, default=0.0)
    success_rate = Column(Float, default=100.0)
    is_healthy = Column(Boolean, default=True)
    requires_proxy = Column(Boolean, default=False)
    proxy_url = Column(String)
    models = Column(JSON, default=list)  # ["gpt-4", "gpt-3.5-turbo"]
    extra_config = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Model(Base):
    __tablename__ = "models"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    provider_id = Column(String)
    model_id = Column(String, nullable=False)  # Provider's internal model ID
    mode = Column(String, default="chat")  # chat | completion | embedding
    input_cost_per_1m = Column(Float, default=0.0)  # $/1M input tokens
    output_cost_per_1m = Column(Float, default=0.0)  # $/1M output tokens
    context_window = Column(Integer, default=8192)
    supports_functions = Column(Boolean, default=False)
    supports_vision = Column(Boolean, default=False)
    enabled = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class RoutingRule(Base):
    __tablename__ = "routing_rules"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    strategy = Column(String, nullable=False)  # fallback | cost | latency | round_robin | weighted | priority
    model_pattern = Column(String)  # e.g. "gpt-4*" or "*"
    provider_order = Column(JSON, default=list)  # ["openai", "anthropic", "deepseek"]
    weights = Column(JSON, default=dict)  # {"openai": 0.5, "anthropic": 0.5}
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=0)
    fallback_enabled = Column(Boolean, default=True)
    max_retries = Column(Integer, default=2)
    timeout_ms = Column(Integer, default=60000)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String)
    role = Column(String, default="user")  # admin | user | readonly
    credits = Column(Integer, default=100)
    is_active = Column(Boolean, default=True)
    api_key = Column(String, unique=True)
    extra_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(String, primary_key=True)
    key = Column(String, unique=True, nullable=False)
    user_id = Column(String)
    name = Column(String)
    prefix = Column(String)
    rate_limit_rpm = Column(Integer, default=60)
    rate_limit_tpm = Column(Integer, default=100000)
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class RequestLog(Base):
    __tablename__ = "request_logs"

    id = Column(String, primary_key=True)
    user_id = Column(String)
    api_key_id = Column(String)
    provider = Column(String)
    model = Column(String)
    mode = Column(String)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    latency_ms = Column(Float, default=0.0)
    status_code = Column(Integer)
    error = Column(Text)
    cache_hit = Column(Boolean, default=False)
    request_metadata = Column(JSON, default=dict)
    cost_usd = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_req_logs_created", "created_at"),
        Index("idx_req_logs_user", "user_id"),
    )


class UsageStats(Base):
    __tablename__ = "usage_stats"

    id = Column(String, primary_key=True)
    user_id = Column(String)
    provider = Column(String)
    model = Column(String)
    total_requests = Column(Integer, default=0)
    total_input_tokens = Column(Integer, default=0)
    total_output_tokens = Column(Integer, default=0)
    total_cost_usd = Column(Float, default=0.0)
    avg_latency_ms = Column(Float, default=0.0)
    period = Column(String)  # daily | monthly
    period_date = Column(String)  # "2026-05-29"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_usage_stats_period", "period_date"),
    )
