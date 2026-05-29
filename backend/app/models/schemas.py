"""Pydantic schemas for all API request/response models."""
from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime


# ---------------------------------------------------------------------------
# Provider Schemas
# ---------------------------------------------------------------------------
class ProviderCreate(BaseModel):
    name: str
    provider_type: str = Field(default="openai")
    base_url: str = Field(default="https://api.openai.com/v1")
    api_key: str = Field(default="")
    headers: dict = Field(default_factory=dict)
    models: list[str] = Field(default_factory=list)
    timeout: int = Field(default=60, ge=5, le=300)
    retry_policy: dict = Field(default_factory=lambda: {"max_retries": 3, "backoff_factor": 1.5})
    weight: int = Field(default=100, ge=1, le=1000)
    region: Optional[str] = None
    is_default: bool = False
    extra: dict = Field(default_factory=dict)


class ProviderUpdate(BaseModel):
    name: Optional[str] = None
    provider_type: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    headers: Optional[dict] = None
    models: Optional[list[str]] = None
    timeout: Optional[int] = None
    retry_policy: Optional[dict] = None
    weight: Optional[int] = None
    region: Optional[str] = None
    status: Optional[str] = None
    is_default: Optional[bool] = None
    extra: Optional[dict] = None


class ProviderResponse(BaseModel):
    id: str
    name: str
    provider_type: str
    base_url: str
    status: str
    is_default: bool
    total_requests: int = 0
    failed_requests: int = 0
    avg_latency_ms: float = 0.0
    avg_cost_per_1k: float = 0.0
    last_seen_at: Optional[datetime] = None
    created_at: datetime
    models: list[str] = []
    weight: int = 100
    region: Optional[str] = None


class ProviderTestResult(BaseModel):
    success: bool
    latency_ms: float = 0.0
    status_code: int = 0
    error: Optional[str] = None
    models_detected: list[str] = []
    streaming_supported: bool = False
    message: str = ""


# ---------------------------------------------------------------------------
# Model Schemas
# ---------------------------------------------------------------------------
class GatewayModelCreate(BaseModel):
    model_config = {"protected_namespaces": ()}
    id: str
    name: str
    provider_id: Optional[str] = None
    model_type: str = Field(default="chat")
    enabled: bool = True
    hidden: bool = False
    extra_params: dict = Field(default_factory=dict)
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    context_window: Optional[int] = None


class GatewayModelUpdate(BaseModel):
    model_config = {"protected_namespaces": ()}
    name: Optional[str] = None
    provider_id: Optional[str] = None
    model_type: Optional[str] = None
    enabled: Optional[bool] = None
    hidden: Optional[bool] = None
    extra_params: Optional[dict] = None
    cost_per_1k_input: Optional[float] = None
    cost_per_1k_output: Optional[float] = None
    context_window: Optional[int] = None


class GatewayModelResponse(BaseModel):
    model_config = {"protected_namespaces": ()}
    id: str
    name: str
    provider_id: Optional[str]
    model_type: str
    enabled: bool
    hidden: bool
    cost_per_1k_input: float
    cost_per_1k_output: float
    context_window: Optional[int]
    created_at: datetime


# ---------------------------------------------------------------------------
# User Schemas
# ---------------------------------------------------------------------------
class UserCreate(BaseModel):
    email: str
    password: Optional[str] = None
    name: str = ""
    role: str = "user"
    rate_limit: int = Field(default=100, ge=1)
    burst_limit: int = Field(default=20, ge=1)
    max_tokens: int = Field(default=-1)
    credits: float = 0.0
    allowed_ips: list[str] = Field(default_factory=list)


class UserUpdate(BaseModel):
    email: Optional[str] = None
    name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    rate_limit: Optional[int] = None
    burst_limit: Optional[int] = None
    max_tokens: Optional[int] = None
    credits: Optional[float] = None
    allowed_ips: Optional[list[str]] = None
    trusted: Optional[bool] = None


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    is_active: bool
    is_verified: bool
    rate_limit: int
    burst_limit: int
    max_tokens: int
    credits: float
    allowed_ips: list[str]
    trusted: bool
    created_at: datetime


# ---------------------------------------------------------------------------
# Routing Schemas
# ---------------------------------------------------------------------------
class RoutingRuleCreate(BaseModel):
    name: str
    strategy: str = Field(default="latency")
    provider_id: Optional[str] = None
    models: list[str] = Field(default_factory=list)
    priority: int = Field(default=50, ge=1, le=100)
    is_active: bool = True
    conditions: dict = Field(default_factory=dict)


class RoutingRuleUpdate(BaseModel):
    name: Optional[str] = None
    strategy: Optional[str] = None
    provider_id: Optional[str] = None
    models: Optional[list[str]] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None
    conditions: Optional[dict] = None


class RoutingRuleResponse(BaseModel):
    id: str
    name: str
    strategy: str
    provider_id: Optional[str]
    models: list[str]
    priority: int
    is_active: bool
    created_at: datetime


# ---------------------------------------------------------------------------
# Analytics Schemas
# ---------------------------------------------------------------------------
class AnalyticsOverview(BaseModel):
    total_requests: int
    total_users: int
    total_providers: int
    total_tokens_used: int
    total_cost: float
    avg_latency_ms: float
    cache_hit_rate: float
    error_rate: float
    requests_by_model: dict
    requests_by_provider: dict
    requests_today: int
    requests_this_week: int


class CostBreakdown(BaseModel):
    date: str
    cost: float
    requests: int
    tokens: int
    provider: str


class LatencyStats(BaseModel):
    provider: str
    avg_latency_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    total_requests: int


# ---------------------------------------------------------------------------
# Config / Feature Flags
# ---------------------------------------------------------------------------
class FeatureFlagCreate(BaseModel):
    key: str
    description: str = ""
    is_enabled: bool = True


class SystemConfigUpdate(BaseModel):
    key: str
    value: Any
    description: str = ""


class SystemConfigResponse(BaseModel):
    key: str
    value: Any
    description: str = ""
    updated_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# OpenAI-Compatible Schemas
# ---------------------------------------------------------------------------
class ChatCompletionRequest(BaseModel):
    model: str = Field(default="gpt-4o")
    messages: list[dict]
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=-1, ge=-1)
    stream: bool = False
    stream_options: Optional[dict] = None
    stop: Optional[list[str]] = None
    frequency_penalty: float = Field(default=0.0, ge=-2, le=2)
    presence_penalty: float = Field(default=0.0, ge=-2, le=2)
    top_p: float = Field(default=1.0, ge=0, le=1)
    user: Optional[str] = None
    tools: Optional[list[dict]] = None
    tool_choice: Optional[str] = None
    response_format: Optional[dict] = None


class ChatCompletionChoice(BaseModel):
    index: int
    message: dict
    finish_reason: Optional[str] = None


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[ChatCompletionChoice]
    usage: dict = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: dict = Field(
        default_factory=lambda: {
            "message": "An error occurred",
            "type": "internal_error",
            "code": "internal_error",
        }
    )
