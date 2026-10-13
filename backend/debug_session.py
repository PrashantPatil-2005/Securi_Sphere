import asyncio
from app.database import async_session

async def f():
    async with async_session() as s:
        print('session type:', type(s))
        print('session class:', s.__class__)
        try:
            await s.execute('SELECT 1')
            print('query ok')
        except Exception as e:
            print('query error:', e)
    # Try another session
    async with async_session() as s2:
        print('second session type:', type(s2))
        try:
            await s2.execute('SELECT 1')
            print('second query ok')
        except Exception as e:
            print('second query error:', e)

asyncio.run(f())