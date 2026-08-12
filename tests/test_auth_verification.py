import asyncio
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

DB_FILE = Path(tempfile.gettempdir()) / 'saki-auth-test.db'
if DB_FILE.exists():
    DB_FILE.unlink()
os.environ.update({
    'USE_D1': 'false',
    'DATABASE_URL': f'sqlite+aiosqlite:///{DB_FILE}',
    'ADMIN_EMAIL': 'admin@example.test',
    'ADMIN_PASSWORD': 'AdminPass!123',
    'SECRET_KEY': 'test-secret',
    'RESEND_API_KEY': '',
    'BREVO_SMTP': '',
    'SMTP_HOST': '',
})

import sys
sys.path.insert(0, str(Path(__file__).parents[1] / 'backend'))

from app.db.session import engine, async_session_maker
from app.db.models import Base, User, VerificationToken
from app.db.migrations import migrate_auth_schema, cleanup_legacy_users
from app.core.auth import hash_password, verify_password, create_access_token
from sqlalchemy import select
from app.api.v1 import admin

captured = []

async def fake_email(recipient, code, verification_url=None):
    captured.append((recipient, code))
admin.send_verification_email = fake_email

async def setup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_session_maker() as session:
        session.add(User(id='admin-001', name='Admin', email='admin@example.test', hashed_password=hash_password('AdminPass!123'), role='admin', is_active=True, api_key='sk-admin'))
        session.add(User(id='old-user', name='Old', email='old@example.test', hashed_password=hash_password('old-pass'), role='user', is_active=True, api_key='sk-old'))
        await session.commit()
    await migrate_auth_schema()
    await cleanup_legacy_users()

async def main():
    await setup()
    async with async_session_maker() as session:
        users = (await session.execute(select(User))).scalars().all()
        assert [u.email for u in users] == ['admin@example.test']
        admin_user = users[0]
        assert admin_user.api_key == 'sk-admin'
        assert admin_user.email_verified_at is not None

    assert verify_password('AdminPass!123', users[0].hashed_password)
    assert not verify_password('wrong', users[0].hashed_password)

    now = datetime.utcnow()
    async with async_session_maker() as session:
        user = User(id='new-user', name='New User', email='new@example.test', hashed_password=hash_password('NewPass!123'), role='user', is_active=False, api_key='sk-new')
        token = VerificationToken(id='token-1', user_id='new-user', token_hash='hash-1', expires_at=now + timedelta(hours=1))
        session.add(user); session.add(token); await session.commit()
        loaded = (await session.execute(select(User).where(User.email == 'new@example.test'))).scalar_one()
        assert loaded.is_active is False and loaded.email_verified_at is None

    assert len(captured) == 0
    expired = VerificationToken(id='token-expired', user_id='new-user', token_hash='hash-expired', expires_at=now - timedelta(minutes=1))
    async with async_session_maker() as session:
        session.add(expired); await session.commit()
    assert create_access_token({'sub': 'new-user', 'role': 'user'})
    print('auth verification unit checks: PASS')

if __name__ == '__main__':
    asyncio.run(main())
