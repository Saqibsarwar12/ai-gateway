import asyncio, os, tempfile
from pathlib import Path
DB_FILE=Path(tempfile.gettempdir())/'saki-security-test.db'
if DB_FILE.exists(): DB_FILE.unlink()
os.environ.update({'USE_D1':'false','DATABASE_URL':f'sqlite+aiosqlite:///{DB_FILE}','SECRET_KEY':'test-secret','ADMIN_EMAIL':'admin@example.com'})
# Make the cached settings singleton reflect THIS module's env (it was created at first import by an earlier test module)
import sys as _sys
_backend_dir = str(__import__("pathlib").Path(__file__).parents[1] / "backend")
if _backend_dir not in _sys.path:
    _sys.path.insert(0, _backend_dir)
from app.core.config import settings as _settings_singleton
_settings_singleton.refresh_from_env()

import sys
sys.path.insert(0,str(Path(__file__).parents[1]/'backend'))
from sqlalchemy import select
from app.db.session import engine, async_session_maker
from app.db.models import Base, User
from app.core.auth import hash_password, create_access_token
from app.api.v1.admin import require_user, require_admin
from fastapi import HTTPException
from datetime import datetime, timedelta

async def main():
 async with engine.begin() as c: await c.run_sync(Base.metadata.create_all)
 async with async_session_maker() as s:
  s.add(User(id='u1',name='U',email='u@example.com',hashed_password=hash_password('Password!123'),role='user',is_active=True,api_key='sk-u'))
  s.add(User(id='a1',name='A',email='admin@example.com',hashed_password=hash_password('Password!123'),role='admin',is_active=True,api_key='sk-a'))
  await s.commit()
 token=create_access_token({'sub':'u1','role':'user'})
 try: await require_user('Bearer '+token)
 except HTTPException as e: assert e.status_code==403 and 'disabled' not in str(e.detail).lower()
 else: raise AssertionError('unverified protected access must fail')
 admin_token=create_access_token({'sub':'a1','role':'admin'})
 assert (await require_admin('Bearer '+admin_token))['sub']=='a1'
 expired=create_access_token({'sub':'a1','role':'admin'},timedelta(seconds=-1))
 try: await require_admin('Bearer '+expired)
 except HTTPException as e: assert e.status_code==401
 else: raise AssertionError('expired token must fail')
 print('auth security checks: PASS')

if __name__ == '__main__':
    asyncio.run(main())
