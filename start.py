import sys
import os

# Add the backend directory to the path
sys.path.insert(0, r'C:\Users\Prash\Desktop\Securi\backend')

# Now start uvicorn
from uvicorn.main import create_app
import asyncio

async def run():
    config = create_app("app.main:app", host="0.0.0.0", port=8000, reload=True)
    await config.serve()

asyncio.run(run())