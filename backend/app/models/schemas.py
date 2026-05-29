"""Pydantic schemas for API request/response models."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ─── Provider Schemas ───────────────────────────────────
class ProviderCreate(BaseModel):
    name: str
    slug: str
    base_url: str
    api_key: str
    enabled: bool = True
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    daily_limit: int = 0
    priority: int = 1
    tags: list[str] = []
    headers: dict = {}
    timeout_seconds: int = 60
    retry_count: int = 3
    models: list[str] = []


class ProviderUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    enabled: Optional[bool] = None
    cost_per_1k_input: Optional[float] = None
    cost_per_1k_output: Optional[float] = None
    daily_limit: Optional[int] = None
    priority: Optional[int] = None
    tags: Optional[list[str]] = None
    headers: Optional[dict] = None
    timeout_seconds: Optional[int] = None
    retry_count: Optional[int] = None
    models: Optional[list[str]] = None
    status: Optional[str] = None


class ProviderResponse(BaseModel):
    id: str
    name: str
    slug: str
    base_url: str
    enabled: bool
    status: str
    latency_ms: int
    cost_per_1k_input: float
    cost_per_1k_output: float
    daily_limit: int
    used_today: int
    priority: int
    tags: list[str]
    models: list[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Routing Schemas ─────────────────────────────────────
class RoutingRuleCreate(BaseModel):
    name: str
    strategy: str
    provider_ids: list[str]
    enabled: bool = True
    conditions: dict = {}


class RoutingRuleUpdate(BaseModel):
    name: Optional[str] = None
    strategy: Optional[str] = None
    provider_ids: Optional[list[str]] = None
    enabled: Optional[bool] = None
    conditions: Optional[dict] = None
    priority: Optional[int] = None


class RoutingRuleResponse(BaseModel):
    id: str
    name: str
    strategy: str
    provider_ids: list[str]
    enabled: bool
    conditions: dict
    priority: int
    created_at: datetime

    class Config:
        from_attributes = True


# ─── User Schemas ────────────────────────────────────────
class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: str = "user"


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    credits: Optional[int] = None
    rate_limit: Optional[int] = None
    enabled: Optional[bool] = None
    allowed_providers: Optional[list[str]] = None
    allowed_models: Optional[list[str]] = None


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    api_key: str
    credits: int
    requests_today: int
    rate_limit: int
    enabled: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Chat Completion Schemas ──────────────────────────────
class Message(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[Message]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 4096
    stream: Optional[bool] = False
    top_p: Optional[float] = None
    stop: Optional[list[str]] = None


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list
    usage: dict
