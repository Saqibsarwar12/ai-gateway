"""Pydantic schemas for AI Gateway API."""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Any, List, Dict
from datetime import datetime


# Make all responses ORM-friendly
RESPONSE_CONFIG = ConfigDict(from_attributes=True)


class ChatMessage(BaseModel):
    role: str
    content: str
    name: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2048
    top_p: Optional[float] = 1.0
    stream: Optional[bool] = False
    stop: Optional[Any] = None
    frequency_penalty: Optional[float] = 0.0
    presence_penalty: Optional[float] = 0.0
    user: Optional[str] = None

    class Config:
        extra = "allow"


class ChatMessageResponse(BaseModel):
    role: str
    content: str


class ChatCompletionChoice(BaseModel):
    index: int
    message: ChatMessageResponse
    finish_reason: str


class ChatCompletionUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: ChatCompletionUsage


# ── Provider ────────────────────────────────────────────────
class ProviderCreate(BaseModel):
    id: Optional[str] = None
    name: str
    provider_type: str
    base_url: str
    api_key: Optional[str] = ""
    models: List[str] = []
    enabled: bool = True
    is_active: bool = True
    priority: int = 100
    max_rpm: int = 1000
    max_tpm: int = 100000
    requires_proxy: bool = False
    proxy_url: Optional[str] = None
    extra_config: Dict[str, Any] = {}
    extra_data: Dict[str, Any] = {}

    class Config:
        extra = "allow"


class ProviderUpdate(BaseModel):
    name: Optional[str] = None
    provider_type: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    models: Optional[List[str]] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None
    extra_data: Optional[Dict[str, Any]] = None

    class Config:
        extra = "allow"


class ProviderResponse(BaseModel):
    id: str
    name: str
    provider_type: str
    base_url: str
    api_key: Optional[str] = None
    models: List[str] = []
    is_active: bool = True
    priority: int = 100
    extra_data: Optional[Dict[str, Any]] = None

    model_config = RESPONSE_CONFIG


# ── Routing Rule ─────────────────────────────────────────────
class RoutingRuleCreate(BaseModel):
    name: str
    strategy: str
    provider_ids: List[str]
    model_pattern: str = "*"
    is_active: bool = True
    priority: Optional[int] = None
    weights: Optional[Dict[str, Any]] = None
    fallback_enabled: bool = True
    max_retries: int = 2
    timeout_ms: int = 60000
    extra_data: Optional[Dict[str, Any]] = None

    class Config:
        extra = "allow"


class RoutingRuleUpdate(BaseModel):
    name: Optional[str] = None
    strategy: Optional[str] = None
    provider_ids: Optional[List[str]] = None
    model_pattern: Optional[str] = None
    is_active: Optional[bool] = None

    class Config:
        extra = "allow"


class RoutingRuleResponse(BaseModel):
    model_config = RESPONSE_CONFIG
    id: str
    name: str
    strategy: str
    provider_ids: List[str] = Field(alias="provider_order")
    model_pattern: str
    is_active: bool


# ── User / API Key ───────────────────────────────────────────
class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: Optional[str] = "user"
    credits: int = 100
    extra_metadata: Optional[Dict[str, Any]] = {}


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    credits: int
    is_active: bool
    api_key: Optional[str] = None
    extra_metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None

    model_config = RESPONSE_CONFIG


class APIKeyResponse(BaseModel):
    id: str
    user_id: str
    key: str
    name: str
    is_active: bool
    created_at: Optional[str] = None

    model_config = RESPONSE_CONFIG


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class UserUpdate(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None
    is_admin: Optional[bool] = None

    class Config:
        extra = "allow"


# ── Analytics ────────────────────────────────────────────────
class DailyStats(BaseModel):
    date: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_tokens: int
    cost_usd: float
    avg_latency_ms: float
    unique_users: int


class AnalyticsResponse(BaseModel):
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_tokens: int
    total_cost: float
    avg_latency_ms: float
    daily_stats: List[DailyStats]


# ── System ───────────────────────────────────────────────────
class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
