"""Pydantic schemas for all API request/response models."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ProviderBase(BaseModel):
    name: str
    provider_type: str = "openai"
    base_url: str = "https://api.openai.com/v1"
    api_key: Optional[str] = None
    enabled: bool = True
    priority: int = 100
    max_rpm: int = 1000
    max_tpm: int = 100000
    requires_proxy: bool = False
    proxy_url: Optional[str] = None
    models: list[str] = []
    extra_config: dict = {}


class ProviderCreate(ProviderBase):
    id: Optional[str] = None


class ProviderUpdate(BaseModel):
    name: Optional[str] = None
    provider_type: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    enabled: Optional[bool] = None
    priority: Optional[int] = None
    max_rpm: Optional[int] = None
    max_tpm: Optional[int] = None
    requires_proxy: Optional[bool] = None
    proxy_url: Optional[str] = None
    models: Optional[list[str]] = None
    extra_config: Optional[dict] = None


class ProviderResponse(ProviderBase):
    id: str
    current_rpm: int = 0
    current_tpm: int = 0
    avg_latency_ms: float = 0.0
    success_rate: float = 100.0
    is_healthy: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RoutingRuleBase(BaseModel):
    model_config = {"protected_namespaces": ()}
    
    name: str
    strategy: str = "fallback"  # fallback | cost | latency | round_robin | weighted | priority
    model_filter: Optional[str] = "*"
    provider_order: list[str] = []
    weights: dict = {}
    is_active: bool = True
    priority: int = 0
    fallback_enabled: bool = True
    max_retries: int = 2
    timeout_ms: int = 60000


class RoutingRuleCreate(RoutingRuleBase):
    pass


class RoutingRuleUpdate(BaseModel):
    model_config = {"protected_namespaces": ()}
    name: Optional[str] = None
    strategy: Optional[str] = None
    model_pattern: Optional[str] = None
    provider_order: Optional[list[str]] = None
    weights: Optional[dict] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None
    fallback_enabled: Optional[bool] = None
    max_retries: Optional[int] = None
    timeout_ms: Optional[int] = None


class RoutingRuleResponse(RoutingRuleBase):
    id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserBase(BaseModel):
    name: str
    email: str
    role: str = "user"
    credits: int = 100


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    credits: Optional[int] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: str
    is_active: bool
    api_key: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ─── Chat Completion Schemas ───────────────────────────────────────────
class Message(BaseModel):
    role: str
    content: str
    name: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    model: str = "gpt-3.5-turbo"
    messages: list[Message]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2048
    top_p: Optional[float] = 1.0
    stop: Optional[list[str]] = None
    stream: Optional[bool] = False
    user: Optional[str] = None


class UsageInfo(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatMessage(BaseModel):
    role: str
    content: str
    index: Optional[int] = None


class ChatCompletionChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[ChatCompletionChoice]
    usage: UsageInfo
