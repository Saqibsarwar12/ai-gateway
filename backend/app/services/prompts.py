"""User-owned custom prompt selection and validation."""
from fnmatch import fnmatchcase

from fastapi import HTTPException
from sqlalchemy import select

from app.db.models import CustomPrompt

MAX_PROMPT_NAME = 80
MAX_PROMPT_PATTERN = 255
MAX_PROMPT_CONTENT = 12000

EXTREME_DIRECTNESS_PROMPT = """Be highly direct and decisive. Lead with the answer. Remove unnecessary hedging, filler, moralizing, repetition, and performative disclaimers. Use concise structure and concrete wording. If a request is ambiguous, state the assumption and proceed. Keep normal accuracy, safety, privacy, legal, and platform constraints; do not invent facts or claim actions you did not take."""


def normalize_prompt_name(value: str) -> str:
    name = " ".join((value or "").strip().split())
    if not 1 <= len(name) <= MAX_PROMPT_NAME:
        raise HTTPException(status_code=400, detail=f"Prompt name must be 1-{MAX_PROMPT_NAME} characters")
    return name


def normalize_model_pattern(value: str) -> str:
    pattern = (value or "*").strip()
    if not 1 <= len(pattern) <= MAX_PROMPT_PATTERN:
        raise HTTPException(status_code=400, detail=f"Model pattern must be 1-{MAX_PROMPT_PATTERN} characters")
    if any(ord(char) < 32 or ord(char) == 127 for char in pattern):
        raise HTTPException(status_code=400, detail="Model pattern contains invalid characters")
    if pattern != "*" and "*" in pattern and not pattern.endswith("*"):
        raise HTTPException(status_code=400, detail="Wildcard is allowed only at the end of a model pattern")
    return pattern


def normalize_prompt_content(value: str) -> str:
    content = (value or "").strip()
    if not 1 <= len(content) <= MAX_PROMPT_CONTENT:
        raise HTTPException(status_code=400, detail=f"Prompt content must be 1-{MAX_PROMPT_CONTENT} characters")
    return content


def resolve_prompt_content(preset: str, value: str) -> str:
    if preset == "extreme_directness":
        return EXTREME_DIRECTNESS_PROMPT
    return normalize_prompt_content(value)


def prompt_matches(prompt: CustomPrompt, model: str) -> bool:
    return bool(prompt.is_active and fnmatchcase(model, prompt.model_pattern or "*"))


async def load_user_prompt(session, user_id: str, model: str, prompt_id: str | None = None) -> CustomPrompt | None:
    if prompt_id:
        result = await session.execute(
            select(CustomPrompt).where(
                CustomPrompt.id == prompt_id,
                CustomPrompt.user_id == user_id,
                CustomPrompt.is_active == True,
            )
        )
        prompt = result.scalar_one_or_none()
        if not prompt:
            raise HTTPException(status_code=404, detail="Prompt not found or not available for this account")
        if not prompt_matches(prompt, model):
            raise HTTPException(status_code=400, detail="Selected prompt does not match the requested model")
        return prompt

    result = await session.execute(
        select(CustomPrompt)
        .where(
            CustomPrompt.user_id == user_id,
            CustomPrompt.is_active == True,
            CustomPrompt.is_default == True,
        )
        .order_by(CustomPrompt.updated_at.desc(), CustomPrompt.created_at.desc())
    )
    prompts = result.scalars().all()
    matching = [prompt for prompt in prompts if prompt_matches(prompt, model)]
    if not matching:
        return None
    matching.sort(key=lambda prompt: (
        0 if (prompt.model_pattern or "*") == model else 1,
        -(prompt.updated_at.timestamp() if prompt.updated_at else 0),
    ))
    return matching[0]


def combine_with_system_prompt(messages: list[dict], prompt_content: str | None) -> list[dict]:
    if not prompt_content:
        return messages
    result = [dict(message) for message in messages]
    system_indexes = [index for index, message in enumerate(result) if message.get("role") == "system"]
    if system_indexes:
        first = system_indexes[0]
        result[first]["content"] = f"{prompt_content}\n\n{result[first].get('content', '')}".strip()
        for index in reversed(system_indexes[1:]):
            result.pop(index)
    else:
        result.insert(0, {"role": "system", "content": prompt_content})
    return result


def prompt_response(prompt: CustomPrompt) -> dict:
    return {
        "id": prompt.id,
        "name": prompt.name,
        "model_pattern": prompt.model_pattern,
        "content": prompt.content,
        "preset": prompt.preset,
        "is_active": bool(prompt.is_active),
        "is_default": bool(prompt.is_default),
        "created_at": prompt.created_at.isoformat() if prompt.created_at else None,
        "updated_at": prompt.updated_at.isoformat() if prompt.updated_at else None,
    }
