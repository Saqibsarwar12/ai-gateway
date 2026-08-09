import re

USERNAME_PATTERN = re.compile(r"^[a-z][a-z0-9-]{1,62}[a-z0-9]$")


def normalize_username(value: str) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"[^a-z0-9-]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value[:64]


def valid_username(value: str) -> bool:
    return bool(USERNAME_PATTERN.fullmatch(value or ""))


def fallback_username(user_id: str) -> str:
    suffix = re.sub(r"[^a-z0-9]", "", (user_id or "").lower())[:12] or "user"
    return f"user-{suffix}"[:64]
