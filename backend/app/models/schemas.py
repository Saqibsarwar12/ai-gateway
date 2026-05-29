"""Pydantic schemas — Pydantic v1 syntax."""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


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
    name: str
    provider_type: str
    base_url: str
    api_key: Optional[str] = ""
    models: List[str] = []
    is_active: bool = True
    priority: int = 100
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
    id: int
    name: str
    provider_type: str
    base_url: str
    models: List[str]
    is_active: bool
    priority: int
    extra_data: Dict[str, Any]
    avg_latency_ms: float
    success_rate: float

    class Config:
        from_attributes = True


# ── Routing Rule ─────────────────────────────────────────────
class RoutingRuleCreate(BaseModel):
    name: str
    strategy: str  # "cheapest" | "priority" | "latency" | "fallback"
    provider_ids: List[int]
    model_pattern: str = "*"
    is_active: bool = True

    class Config:
        extra = "allow"


class RoutingRuleUpdate(BaseModel):
    name: Optional[str] = None
    strategy: Optional[str] = None
    provider_ids: Optional[List[int]] = None
    model_pattern: Optional[str] = None
    is_active: Optional[bool] = None

    class Config:
        extra = "allow"


class RoutingRuleResponse(BaseModel):
    id: int
    name: str
    strategy: str
    provider_ids: List[int]
    model_pattern: str
    is_active: bool

    class Config:
        from_attributes = True


# ── User / API Key ───────────────────────────────────────────
class UserCreate(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    is_admin: bool
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class APIKeyResponse(BaseModel):
    id: int
    user_id: int
    key: str
    name: str
    is_active: bool
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


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
