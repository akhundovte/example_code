import aiopg.sa

from aiopg.sa.engine import get_dialect

from utils.json_serializer import json_dumps_extend
from ..base_engine import BaseDBEngine


class DBEngine(BaseDBEngine):

    async def get_new_engine(self, conn_params):
        # важно aiopg при создании engine формирует пул соединений с БД
        # по умолчанию размер пула 10
        return await aiopg.sa.create_engine(
            **conn_params,
            dialect=get_dialect(json_serializer=json_dumps_extend),
            )

    def acquire(self):
        """Обертки, чтобы выполнять методы без обращения к атрибуту engine"""
        return self._engine.acquire()

    def release(self, conn):
        return self._engine.release(conn)
