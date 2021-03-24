
from functools import wraps
from db import db_engine as db


def db_connect_classmethod(method):
    @wraps(method)
    async def decorated(self, *args, **kwargs):
        async with db.engine.acquire() as db_connection:
            return await method(self, db_connection, *args, **kwargs)
    return decorated
