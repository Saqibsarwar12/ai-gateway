import asyncio, os, tempfile
from pathlib import Path
DB_FILE=Path(tempfile.gettempdir())/'saki-expiry-test.db'
if DB_FILE.exists(): DB_FILE.unlink()
os.environ.update({'USE_D1':'false','DATABASE_URL':f'sqlite+aiosqlite:///{DB_FILE}','ADMIN_EMAIL':'admin@example.com','SECRET_KEY':'test-secret','VERIFICATION_TOKEN_HOURS':'0'})
import sys
sys.path.insert(0,str(Path(__file__).parents[1]/'backend'))
from sqlalchemy import select
from app.db.session import engine, async_session_maker
from app.db.models import Base, User, VerificationToken
from app.core.auth import hash_password
from app.api.v1 import admin
from app.api.v1.admin import RegisterBody, verify_code, VerifyCodeBody
from app.core.config import settings
from datetime import datetime, timedelta
from fastapi import HTTPException
from starlette.requests import Request

async def main():
 async with engine.begin() as c: await c.run_sync(Base.metadata.create_all)
 async def fake(recipient, code): pass
 admin.send_verification_email=fake
 req=Request({'type':'http','method':'POST','path':'/','headers':[(b'x-forwarded-for',b'8.8.8.8')]})
 await admin.register(RegisterBody(name='Expired',email='expired@example.com',password='Password!123'),req)
 async with async_session_maker() as s:
  row=(await s.execute(select(__import__('app.db.models', fromlist=['PendingRegistration']).PendingRegistration))).scalar_one()
  row.expires_at=datetime.utcnow()-timedelta(minutes=1)
  await s.commit()
  token_hash=row.token_hash
 try:
  await verify_code(VerifyCodeBody(email='expired@example.com', code='0000'))
 except HTTPException as e: assert e.status_code==400
 else: raise AssertionError('expired code must fail')
 try:
  await verify_code(VerifyCodeBody(email='expired@example.com', code='0000'))
 except HTTPException as e: assert e.status_code==400
 print('expiry/invalid token checks: PASS')

if __name__ == '__main__':
    asyncio.run(main())
