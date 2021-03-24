

# пока не использовал, но можно попробовать вместо декораторов в repository
class Pool:
    """
    Обертка работы с драйвером БД
    чтобы спрятать взятие коннекции из пула соединений
    """

    def __init__(self, db_engine):
        self.db_engine = db_engine

    async def execute(self, query):
        async with self.db_engine.acquire() as db_connection:
            await db_connection.execute(query)

    async def fetchall(self, query):
        async with self.db_engine.acquire() as db_connection:
            result = await db_connection.execute(query)
            return await result.fetchall()

    async def first(self, query):
        async with self.db_engine.acquire() as db_connection:
            result = await db_connection.execute(query)
            return await result.first()

    async def fetchone(self, query):
        async with self.db_engine.acquire() as db_connection:
            result = await db_connection.execute(query)
            return await result.fetchone()

    async def fetchmany(self, query, size):
        async with self.db_engine.acquire() as db_connection:
            result = await db_connection.execute(query)
            return await result.fetchmany(size)