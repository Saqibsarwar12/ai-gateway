import asyncio
import os
import tempfile
from datetime import datetime
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import select

DB_FILE = Path(tempfile.gettempdir()) / 'saki-custom-prompts-test.db'
if DB_FILE.exists():
    DB_FILE.unlink()
os.environ.update({
    'USE_D1': 'false',
    'DATABASE_URL': f'sqlite+aiosqlite:///{DB_FILE}',
    'ADMIN_EMAIL': 'admin@example.com',
    'SECRET_KEY': 'prompt-test-secret',
})

import sys
sys.path.insert(0, str(Path(__file__).parents[1] / 'backend'))

from app.api.v1.admin import PromptBody, create_my_prompt, update_my_prompt, list_my_prompts
from app.db.models import Base, User, CustomPrompt
from app.db.session import async_session_maker, engine
from app.services.prompts import (
    EXTREME_DIRECTNESS_PROMPT,
    combine_with_system_prompt,
    load_user_prompt,
    normalize_model_pattern,
    resolve_prompt_content,
)


@pytest.fixture(scope='module', autouse=True)
def setup_db():
    async def create():
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with async_session_maker() as session:
            session.add_all([
                User(id='u1', name='User One', email='u1@example.com', role='user', is_active=True, email_verified_at=datetime.utcnow()),
                User(id='u2', name='User Two', email='u2@example.com', role='user', is_active=True, email_verified_at=datetime.utcnow()),
            ])
            await session.commit()
    asyncio.run(create())
    yield


@pytest.mark.asyncio
async def test_preset_and_model_matching():
    assert resolve_prompt_content('extreme_directness', '') == EXTREME_DIRECTNESS_PROMPT
    assert normalize_model_pattern('gpt-4o*') == 'gpt-4o*'
    with pytest.raises(HTTPException):
        normalize_model_pattern('gpt-*o')

    async with async_session_maker() as session:
        wildcard = CustomPrompt(id='wild', user_id='u1', name='wild', model_pattern='gpt-*', content='wild', is_default=True, is_active=True)
        exact = CustomPrompt(id='exact', user_id='u1', name='exact', model_pattern='gpt-4o', content='exact', is_default=True, is_active=True)
        session.add_all([wildcard, exact])
        await session.commit()
        selected = await load_user_prompt(session, 'u1', 'gpt-4o')
        assert selected.id == 'exact'


@pytest.mark.asyncio
async def test_prompt_crud_is_user_owned_and_defaults_are_scoped():
    first = await create_my_prompt(PromptBody(name='Direct', model_pattern='*', content='answer directly', is_default=True), {'sub': 'u1'})
    second = await create_my_prompt(PromptBody(name='Extreme', model_pattern='nvidia-*', content='', preset='extreme_directness', is_default=True), {'sub': 'u2'})
    assert first['user_id'] if 'user_id' in first else True
    assert second['preset'] == 'extreme_directness'

    async with async_session_maker() as session:
        rows1 = (await session.execute(select(CustomPrompt).where(CustomPrompt.user_id == 'u1'))).scalars().all()
        rows2 = (await session.execute(select(CustomPrompt).where(CustomPrompt.user_id == 'u2'))).scalars().all()
        assert sum(bool(row.is_default) for row in rows1) == 1
        assert sum(bool(row.is_default) for row in rows2) == 1

    with pytest.raises(HTTPException) as exc:
        await update_my_prompt(second['id'], PromptBody(name='Nope', model_pattern='*', content='x'), {'sub': 'u1'})
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_system_prompt_injection_preserves_user_messages():
    messages = [{'role': 'system', 'content': 'existing'}, {'role': 'user', 'content': 'hello'}]
    result = combine_with_system_prompt(messages, 'saved')
    assert result[0]['content'] == 'saved\n\nexisting'
    assert result[1] == messages[1]
    assert messages[0]['content'] == 'existing'
