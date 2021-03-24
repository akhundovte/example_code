import asyncpg

from ..base_engine import BaseDBEngine


class DBEngine(BaseDBEngine):

    async def get_new_engine(self, conn_params):
        return await asyncpg.create_pool(
            **conn_params,
            )
