import asyncio, os, tempfile
from pathlib import Path
DB_FILE=Path(tempfile.gettempdir())/'saki-migration-test.db'
if DB_FILE.exists(): DB_FILE.unlink()
os.environ.update({'USE_D1':'false','DATABASE_URL':f'sqlite+aiosqlite:///{DB_FILE}','ADMIN_EMAIL':'admin@example.com'})
import sys
sys.path.insert(0,str(Path(__file__).parents[1]/'backend'))
from sqlalchemy import select
from app.db.session import engine, async_session_maker
from app.db.models import Base, User, APIKey
from app.core.auth import hash_password
from app.db.migrations import migrate_auth_schema, cleanup_legacy_users

async def main():
    async with engine.begin() as c: await c.run_sync(Base.metadata.create_all)
    async with async_session_maker() as s:
        s.add_all([User(id='admin',name='Admin',email='admin@example.com',hashed_password=hash_password('x'),role='admin',is_active=True,api_key='sk-admin'),User(id='old',name='Old',email='old@example.com',role='user',is_active=True,api_key='sk-old')])
        await s.commit()
    await migrate_auth_schema(); out=await cleanup_legacy_users(); assert out['admin_id']=='admin'
    async with async_session_maker() as s:
        users=(await s.execute(select(User))).scalars().all(); assert len(users)==1 and users[0].id=='admin' and users[0].email_verified_at
        again=await cleanup_legacy_users(); assert again['skipped'] is True
    print('migration preservation/cleanup checks: PASS')

if __name__ == '__main__':
    asyncio.run(main())
