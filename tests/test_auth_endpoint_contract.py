import asyncio, os, tempfile
from pathlib import Path
DB_FILE=Path(tempfile.gettempdir())/'saki-contract-test.db'
if DB_FILE.exists(): DB_FILE.unlink()
os.environ.update({'USE_D1':'false','DATABASE_URL':f'sqlite+aiosqlite:///{DB_FILE}','ADMIN_EMAIL':'admin@example.com','ADMIN_PASSWORD':'AdminPass!123','SECRET_KEY':'test-secret'})
import sys
sys.path.insert(0,str(Path(__file__).parents[1]/'backend'))
from app.main import app
from httpx import ASGITransport, AsyncClient
from app.db.session import engine
from app.db.models import Base

async def main():
 async with engine.begin() as c: await c.run_sync(Base.metadata.create_all)
 async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
  health=await client.get('/health'); assert health.status_code==200 and health.json()['status']=='ok'
  openapi=await client.get('/openapi.json'); assert openapi.status_code==200
 print('endpoint contract checks: PASS')

if __name__ == '__main__':
    asyncio.run(main())
