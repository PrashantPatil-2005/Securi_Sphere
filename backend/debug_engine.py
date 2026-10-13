import inspect
from app.database import async_engine, async_session

print('=== async_engine ===')
print(inspect.getsource(async_engine))
print('=== async_session ===')
print(inspect.getsource(async_session))