import asyncio, os, tempfile
from pathlib import Path
DB_FILE=Path(tempfile.gettempdir())/'saki-guards-test.db'
if DB_FILE.exists(): DB_FILE.unlink()
os.environ.update({'USE_D1':'false','DATABASE_URL':f'sqlite+aiosqlite:///{DB_FILE}','ADMIN_EMAIL':'admin@example.com','SECRET_KEY':'test-secret'})
import sys
sys.path.insert(0,str(Path(__file__).parents[1]/'backend'))
from sqlalchemy import select
from app.db.session import engine, async_session_maker
from app.db.models import Base, User
from app.core.auth import hash_password, create_access_token
from app.api.v1.admin import require_user, require_admin
from app.api.gateway import _resolve_actor
from fastapi import HTTPException

async def main():
 async with engine.begin() as c: await c.run_sync(Base.metadata.create_all)
 async with async_session_maker() as s:
  s.add(User(id='u1',name='Unverified',email='u@example.com',hashed_password=hash_password('Password!123'),role='user',is_active=False,api_key='sk-u'))
  await s.commit()
 token=create_access_token({'sub':'u1','email':'u@example.com','role':'user'})
 try: await require_user(f'Bearer {token}')
 except HTTPException as e: assert e.status_code==403
 else: raise AssertionError('inactive/unverified bearer must fail')
 try: await _resolve_actor(f'Bearer {token}',None)
 except HTTPException as e: assert e.status_code==401
 else: raise AssertionError('inactive/unverified gateway bearer must fail')
 try: await _resolve_actor(None,'sk-u')
 except HTTPException as e: assert e.status_code==401
 else: raise AssertionError('inactive/unverified api key must fail')
 print('protected access guard checks: PASS')
asyncio.run(main())
