"""
Comprehensive auth integration tests for Saki Gateway email-verification flow.
Run: python tests/test_auth_full_flow.py

Tests:
  1. Admin login (no verification required)
  2. Registration creates PendingRegistration, sends code
  3. Login blocked until verified
  4. Wrong code rejected with remaining attempts
  5. Correct code creates verified User
  6. After verification, login succeeds
  7. Resend — generates new code, deletes old pending
  8. Resend blocked for verified users
  9. Duplicate registration blocked (409)
  10. Admin cannot delete themselves
  11. Unverified user blocked on /auth/me
  12. Cleanup migration removes all non-admin users
"""
import asyncio
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

DB_FILE = Path(tempfile.gettempdir()) / 'saki-full-flow-test.db'
if DB_FILE.exists():
    DB_FILE.unlink()

os.environ.update({
    'USE_D1': 'false',
    'DATABASE_URL': f'sqlite+aiosqlite:///{DB_FILE}',
    'ADMIN_EMAIL': 'admin@test.com',
    'ADMIN_PASSWORD': 'AdminPass!123',
    'SECRET_KEY': 'full-flow-test-secret',
})
# Make the cached settings singleton reflect THIS module's env (it was created at first import by an earlier test module)
import sys as _sys
_backend_dir = str(__import__("pathlib").Path(__file__).parents[1] / "backend")
if _backend_dir not in _sys.path:
    _sys.path.insert(0, _backend_dir)
from app.core.config import settings as _settings_singleton
_settings_singleton.refresh_from_env()


import sys
sys.path.insert(0, str(Path(__file__).parents[1] / 'backend'))

from sqlalchemy import select
from app.db.session import engine, async_session_maker
from app.db.models import Base, User, PendingRegistration
from app.db.migrations import migrate_auth_schema, cleanup_legacy_users
from app.core.auth import hash_password, create_access_token
from app.api.v1.admin import (
    login, RegisterBody, LoginBody,
    verify_code, VerifyCodeBody,
    resend_verification, ResendBody,
    delete_user, require_user,
    RegisterBody, LoginBody,
)
from fastapi import HTTPException

captured = []

async def fake_email(recipient, code, verification_url=None):
    captured.append((recipient, code))

from app.api.v1 import admin
admin.send_verification_email = fake_email
admin.settings.EMAIL_FROM = 'noreply@test.com'
admin.settings.BREVO_API_KEY = 'test-key'

def req(ip='127.0.0.1'):
    from starlette.requests import Request
    return Request({'type': 'http', 'method': 'POST', 'path': '/',
                    'headers': [(b'x-forwarded-for', ip.encode())]})


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_maker() as session:
        session.add(User(
            id='admin-001', name='Admin', email='admin@test.com',
            hashed_password=hash_password('AdminPass!123'),
            role='admin', is_active=True,
            email_verified_at=datetime.utcnow(), api_key='sk-admin',
        ))
        session.add(User(
            id='old-user', name='Old User', email='old@test.com',
            hashed_password=hash_password('OldPass!123'),
            role='user', is_active=True,
            email_verified_at=datetime.utcnow(), api_key='sk-old',
        ))
        await session.commit()

    await migrate_auth_schema()
    result = await cleanup_legacy_users()
    assert result.get('admin_id') == 'admin-001', f"cleanup failed: {result}"
    print('✓ cleanup_legacy_users: only admin preserved')

    async with async_session_maker() as session:
        users = (await session.execute(select(User))).scalars().all()
        assert len(users) == 1, f"Expected 1 user, got {len(users)}"
        assert users[0].email == 'admin@test.com'
    print('✓ only admin user exists after cleanup')

    # ── 1. Admin login ──────────────────────────────────────────────
    captured.clear()
    result = await login(LoginBody(identifier='admin@test.com', password='AdminPass!123'), req('1.1.1.1'))
    assert result['user']['role'] == 'admin' and result['access_token']
    print('✓ admin login works')

    # ── 2. Registration creates pending + sends code ────────────────
    captured.clear()
    result = await admin.register(RegisterBody(
        name='New User', email='newuser@test.com', password='NewUser!123'
    ), req('2.2.2.2'))
    assert result['status'] == 'verification_required'
    assert len(captured) == 1
    code = captured[0][1]
    assert len(code) == 6 and code.isdigit()
    print(f'✓ registration creates pending + sends code {code}')

    # ── 3. Login blocked for unverified ──────────────────────────────
    try:
        await login(LoginBody(identifier='newuser@test.com', password='NewUser!123'), req('2.2.2.2'))
        raise AssertionError('unverified login should be blocked')
    except HTTPException as e:
        assert e.status_code == 401
        assert 'X-Needs-Verification' in e.headers
    print('✓ unverified login blocked with X-Needs-Verification header')

    # ── 4. Wrong code rejected ─────────────────────────────────────
    try:
        await verify_code(VerifyCodeBody(email='newuser@test.com', code='000000'))
        raise AssertionError('wrong code should fail')
    except HTTPException as e:
        assert e.status_code == 400
        assert 'incorrect' in str(e.detail).lower()
    print('✓ wrong code rejected')

    # ── 5. Correct code creates verified user ──────────────────────
    result = await verify_code(VerifyCodeBody(email='newuser@test.com', code=code))
    assert result['verified'] is True
    assert result['user']['email'] == 'newuser@test.com'
    async with async_session_maker() as session:
        u = (await session.execute(select(User).where(User.email == 'newuser@test.com'))).scalar_one()
        assert u.email_verified_at is not None
        assert u.role == 'user'
    print('✓ correct code creates verified user')

    # ── 6. After verification, login succeeds ───────────────────────
    captured.clear()
    result = await login(LoginBody(identifier='newuser@test.com', password='NewUser!123'), req('2.2.2.2'))
    assert result['access_token'] and result['user']['email'] == 'newuser@test.com'
    print('✓ login works after verification')

    # ── 7. Unverified user blocked on /auth/me ──────────────────────
    unverified_token = create_access_token({'sub': 'admin-001', 'role': 'user'})
    # Force admin's email_verified_at to None for this test
    async with async_session_maker() as session:
        u = (await session.execute(select(User).where(User.id == 'admin-001'))).scalar_one()
        u.email_verified_at = None
        await session.commit()
    try:
        await require_user(authorization=f'Bearer {unverified_token}')
        raise AssertionError('unverified user should be blocked on /auth/me')
    except HTTPException as e:
        assert e.status_code == 403
        assert 'verify' in str(e.detail).lower()
    # Restore
    async with async_session_maker() as session:
        u = (await session.execute(select(User).where(User.id == 'admin-001'))).scalar_one()
        u.email_verified_at = datetime.utcnow()
        await session.commit()
    print('✓ unverified user blocked on require_user (non-admin)')

    # ── 8. Resend — new code, old pending deleted ─────────────────
    captured.clear()
    result = await admin.register(RegisterBody(
        name='Resend User', email='resend@test.com', password='Resend!123'
    ), req('3.3.3.3'))
    assert result['status'] == 'verification_required'
    old_code = captured[0][1]

    captured.clear()
    result = await resend_verification(
        ResendBody(email='resend@test.com'),
        req('3.3.3.3'),
    )
    assert result['status'] == 'verification_required'
    new_code = captured[0][1]
    assert new_code != old_code
    async with async_session_maker() as session:
        pendings = (await session.execute(
            select(PendingRegistration).where(PendingRegistration.email == 'resend@test.com')
        )).scalars().all()
        assert len(pendings) == 1, f'Expected 1 pending, got {len(pendings)}'
    print(f'✓ resend: new code {new_code}, old pending deleted')

    # ── 9. Resend blocked for verified users ───────────────────────
    try:
        await resend_verification(ResendBody(email='newuser@test.com'), req('3.3.3.3'))
        raise AssertionError('resend for verified user should fail')
    except HTTPException as e:
        assert e.status_code == 409
    print('✓ resend blocked for already-verified users')

    # ── 10. Duplicate registration blocked ─────────────────────────
    try:
        await admin.register(RegisterBody(
            name='Another', email='newuser@test.com', password='Another!123'
        ), req('4.4.4.4'))
        raise AssertionError('duplicate registration should fail')
    except HTTPException as e:
        assert e.status_code == 409
    print('✓ duplicate registration blocked (409)')

    # ── 11. Admin cannot delete themselves ─────────────────────────
    admin_token = create_access_token({'sub': 'admin-001', 'role': 'admin'})
    try:
        await delete_user('admin-001', {'sub': 'admin-001', 'role': 'admin'})
        raise AssertionError('admin self-delete should fail')
    except HTTPException as e:
        assert e.status_code == 403
    print('✓ admin cannot delete themselves')

    # ── 12. Cleanup removes non-admin users ────────────────────────
    async with async_session_maker() as session:
        u = User(
            id='temp-user', name='Temp', email='temp@test.com',
            hashed_password=hash_password('Temp!123'),
            role='user', is_active=True,
            email_verified_at=datetime.utcnow(), api_key='sk-temp',
        )
        session.add(u)
        await session.commit()

    await migrate_auth_schema()
    result = await cleanup_legacy_users()
    assert result.get('admin_id') == 'admin-001'
    async with async_session_maker() as session:
        users = (await session.execute(select(User))).scalars().all()
        assert len(users) == 1 and users[0].id == 'admin-001'
    print('✓ cleanup removes all non-admin users')

    print('\n✅ All 12 auth flow tests PASSED')


if __name__ == '__main__':
    asyncio.run(main())
