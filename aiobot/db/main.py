import aiopg.sa

from utils.json_serializer import json_dumps_extend
from aiopg.sa.engine import get_dialect


async def pg_engine(app):
    conf = app['config']['postgres_db']
    app['db'] = await aiopg.sa.create_engine(
        database=conf['database'],
        user=conf['user'],
        password=conf['password'],
        host=conf['host'],
        port=conf['port'],
        minsize=conf['minsize'],
        maxsize=conf['maxsize'],
        echo=conf['echo'],
        dialect=get_dialect(json_serializer=json_dumps_extend),
        )
    yield
    app['db'].close()
    await app['db'].wait_closed()
