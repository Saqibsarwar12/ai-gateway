"""SQLAlchemy models for AI Gateway."""
from sqlalchemy import Column, String, Text, Boolean, Integer, Float, JSON, DateTime, ForeignKey, Index
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base
import enum


class UserRole(enum.Enum):
    ADMIN = "admin"
    STAFF = "staff"
    USER = "user"
    ENTERPRISE = "enterprise"


class ProviderStatus(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    UNKNOWN = "unknown"


class RoutingStrategy(enum.Enum):
    LATENCY = "latency"
    COST = "cost"
    WEIGHTED = "weighted"
    FAILOVER = "failover"
    PRIORITY = "priority"


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------
class ProviderModel(Base):
    __tablename__ = "providers"

    id = Column(String(64), primary_key=True)
    name = Column(String(255), nullable=False)
    provider_type = Column(String(64), nullable=False)
    base_url = Column(String(512), nullable=False)
    api_key = Column(Text, nullable=False)
    headers = Column(JSON, default={})
    models = Column(JSON, default=[])
    timeout = Column(Integer, default=60)
    retry_policy = Column(JSON, default={"max_retries": 3, "backoff_factor": 1.5})
    weight = Column(Integer, default=100)
    region = Column(String(64), nullable=True)
    status = Column(SAEnum(ProviderStatus), default=ProviderStatus.ACTIVE)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    total_requests = Column(Integer, default=0)
    failed_requests = Column(Integer, default=0)
    avg_latency_ms = Column(Float, default=0.0)
    avg_cost_per_1k = Column(Float, default=0.0)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)

    extra = Column(JSON, default={})

    routes = relationship("RoutingRuleModel", back_populates="provider")
    user_assignments = relationship("UserProviderAssignment", back_populates="provider")


# ---------------------------------------------------------------------------
# Gateway Models
# ---------------------------------------------------------------------------
class GatewayModel(Base):
    __tablename__ = "gateway_models"

    id = Column(String(128), primary_key=True)
    name = Column(String(255), nullable=False)
    provider_id = Column(String(64), ForeignKey("providers.id"), nullable=True)
    model_type = Column(String(64), nullable=False)
    enabled = Column(Boolean, default=True)
    hidden = Column(Boolean, default=False)
    extra_params = Column(JSON, default={})
    cost_per_1k_input = Column(Float, default=0.0)
    cost_per_1k_output = Column(Float, default=0.0)
    context_window = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(String(64), primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)
    name = Column(String(255), default="")
    role = Column(SAEnum(UserRole), default=UserRole.USER)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    ip_whitelist = Column(JSON, default=[])
    allowed_ips = Column(JSON, default=[])
    rate_limit = Column(Integer, default=100)
    burst_limit = Column(Integer, default=20)
    max_tokens = Column(Integer, default=-1)
    trusted = Column(Boolean, default=False)
    credits = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
    routes = relationship("UserRoutingRule", back_populates="user")
    assignments = relationship("UserProviderAssignment", back_populates="user")


# ---------------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------------
class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), ForeignKey("users.id"), nullable=False)
    key_hash = Column(String(255), nullable=False)
    key_prefix = Column(String(16), nullable=False)
    name = Column(String(255), default="")
    is_active = Column(Boolean, default=True)
    expires_on = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="api_keys")
    __table_args__ = (Index("ix_api_keys_key_hash", "key_hash"),)


# ---------------------------------------------------------------------------
# Routing Rules
# ---------------------------------------------------------------------------
class RoutingRuleModel(Base):
    __tablename__ = "routing_rules"

    id = Column(String(64), primary_key=True)
    name = Column(String(255), nullable=False)
    strategy = Column(SAEnum(RoutingStrategy), default=RoutingStrategy.LATENCY, nullable=False)
    provider_id = Column(String(64), ForeignKey("providers.id"), nullable=True)
    models = Column(JSON, default=[])
    priority = Column(Integer, default=50)
    is_active = Column(Boolean, default=True)
    conditions = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    provider = relationship("ProviderModel", back_populates="routes")
    user_routes = relationship("UserRoutingRule", back_populates="rule")


class UserRoutingRule(Base):
    __tablename__ = "user_routing_rules"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), ForeignKey("users.id"), nullable=False)
    rule_id = Column(String(64), ForeignKey("routing_rules.id"), nullable=False)

    user = relationship("User", back_populates="routes")
    rule = relationship("RoutingRuleModel", back_populates="user_routes")


# ---------------------------------------------------------------------------
# User-Provider Assignments
# ---------------------------------------------------------------------------
class UserProviderAssignment(Base):
    __tablename__ = "user_provider_assignments"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), ForeignKey("users.id"), nullable=False)
    provider_id = Column(String(64), ForeignKey("providers.id"), nullable=False)
    rate_limit = Column(Integer, default=None)

    user = relationship("User", back_populates="assignments")
    provider = relationship("ProviderModel", back_populates="user_assignments")


# ---------------------------------------------------------------------------
# Request Logs
# ---------------------------------------------------------------------------
class RequestLog(Base):
    __tablename__ = "request_logs"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), ForeignKey("users.id"), nullable=True)
    api_key_id = Column(String(64), nullable=True)
    model = Column(String(128), nullable=False)
    provider_id = Column(String(64), ForeignKey("providers.id"), nullable=True)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    latency_ms = Column(Float, default=0.0)
    status_code = Column(Integer, default=200)
    error = Column(Text, nullable=True)
    cache_hit = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_request_logs_created_at", "created_at"),
        Index("ix_request_logs_user_id", "user_id"),
    )


# ---------------------------------------------------------------------------
# Feature Flags
# ---------------------------------------------------------------------------
class FeatureFlag(Base):
    __tablename__ = "feature_flags"

    id = Column(String(64), primary_key=True)
    key = Column(String(128), unique=True, nullable=False)
    description = Column(Text, default="")
    is_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------------
# System Config
# ---------------------------------------------------------------------------
class SystemConfig(Base):
    __tablename__ = "system_config"

    id = Column(String(64), primary_key=True)
    key = Column(String(128), unique=True, nullable=False)
    value = Column(JSON, nullable=False)
    description = Column(Text, default="")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
