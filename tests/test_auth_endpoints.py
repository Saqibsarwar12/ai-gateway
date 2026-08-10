import asyncio
import os
import tempfile
from pathlib import Path

DB_FILE = Path(tempfile.gettempdir()) / 'saki-endpoint-test.db'
if DB_FILE.exists(): DB_FILE.unlink()
os.environ.update({
    'USE_D1': 'false',
    'DATABASE_URL': f'sqlite+aiosqlite:///{DB_FILE}',
    'ADMIN_EMAIL': 'admin@example.com',
    'ADMIN_PASSWORD': 'AdminPass!123',
    'SECRET_KEY': 'test-secret',
})
import sys
sys.path.insert(0, str(Path(__file__).parents[1] / 'backend'))
from app.db.session import engine, async_session_maker
from app.db.models import Base, User, PendingRegistration
from app.core.auth import hash_password
from app.api.v1 import admin
from app.api.v1.admin import LoginBody, RegisterBody, login, register, verify_code, VerifyCodeBody
from fastapi import HTTPException
from starlette.requests import Request
from sqlalchemy import select

captured=[]
async def fake_email(recipient, code): captured.append((recipient, code))
admin.settings.BREVO_API_KEY='configured-test-key'
admin.settings.EMAIL_FROM='noreply@example.com'
admin.send_verification_email=fake_email

def req(ip='127.0.0.1'):
    return Request({'type':'http','method':'POST','path':'/','headers':[(b'x-forwarded-for',ip.encode())]})

async def main():
    async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
    async with async_session_maker() as session:
        session.add(User(id='admin-001',name='Admin',email='admin@example.com',hashed_password=hash_password('AdminPass!123'),role='admin',is_active=True,email_verified_at=__import__('datetime').datetime.utcnow(),api_key='sk-admin'))
        await session.commit()
    result=await login(LoginBody(identifier='admin@example.com',password='AdminPass!123'),req('1.1.1.1'))
    assert result['user']['role']=='admin' and result['access_token']
    async def failing_email(recipient, code):
        raise admin.EmailDeliveryError('not configured')
    admin.send_verification_email=failing_email
    try:
        await register(RegisterBody(name='New User',email='new@example.com',password='NewPass!123'),req('2.2.2.2'))
    except HTTPException as e:
        assert e.status_code==503
    else: raise AssertionError('unconfigured sender must fail closed')
    admin.send_verification_email=fake_email
    admin.settings.BREVO_API_KEY='test-key'; admin.settings.EMAIL_FROM='noreply@example.com'
    out=await register(RegisterBody(name='New User',email='new@example.com',password='NewPass!123'),req('3.3.3.3'))
    assert out['status']=='verification_required' and captured
    try: await login(LoginBody(identifier='new@example.com',password='NewPass!123'),req('3.3.3.3'))
    except HTTPException as e: assert e.status_code == 401
    else: raise AssertionError('unverified login must fail')
    verified=await verify_code(VerifyCodeBody(email='new@example.com',code=captured[-1][1]))
    assert verified['verified'] is True
    logged=await login(LoginBody(identifier='new@example.com',password='NewPass!123'),req('3.3.3.3'))
    assert logged['user']['email']=='new@example.com'
    try: await verify_code(VerifyCodeBody(email='new@example.com', code=captured[-1][1]))
    except HTTPException as e: assert e.status_code==400
    else: raise AssertionError('code reuse must fail')
    try: await register(RegisterBody(name='Another',email='new@example.com',password='NewPass!123'),req('4.4.4.4'))
    except HTTPException as e: assert e.status_code==409
    else: raise AssertionError('duplicate registration must fail')
    async with async_session_maker() as session:
        expired=PendingRegistration(id='expired',name='expired',email='expired@example.com',hashed_password=hash_password('NewPass!123'),token_hash='expired-hash',expires_at=__import__('datetime').datetime.utcnow()-__import__('datetime').timedelta(minutes=1),created_at=__import__('datetime').datetime.utcnow())
        session.add(expired); await session.commit()
    try: await verify_code(VerifyCodeBody(email='expired@example.com', code='0000'))
    except HTTPException as e: assert e.status_code==400 and 'expired' in str(e.detail).lower()
    else: raise AssertionError('expired code must fail')
    admin.send_verification_email=failing_email
    try: await register(RegisterBody(name='Delivery Fail',email='fail@example.com',password='NewPass!123'),req('5.5.5.5'))
    except HTTPException as e: assert e.status_code==503
    else: raise AssertionError('delivery failure must fail closed')
    async with async_session_maker() as session:
        assert (await session.execute(select(User).where(User.email=='fail@example.com'))).scalar_one_or_none() is None
    print('auth endpoint checks: PASS')

if __name__ == '__main__':
    asyncio.run(main())
