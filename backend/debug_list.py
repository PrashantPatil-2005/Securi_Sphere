import sys
sys.path.insert(0, '.')
from app import database
items = [x for x in dir(database) if not x.startswith('_')]
print(items)