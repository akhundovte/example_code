from contextlib import asynccontextmanager
from contextvars import ContextVar

from aiopg.sa import SAConnection
from aiopg.sa.transaction import Transaction

connection = ContextVar('connection', default=None)


"""
Два варианта контекстного менеджера

первый вариант более надежный, т.к. используются родные контектсные менеджеры aiopg
второй вариант повторяет действия родных контектсных менеджеров aiopg

второй вариант можно интегрировать в класс
    class SubSaveRepository:
        def begin(self):
            return _TransactionContextManager()

Применяется для выполнения действий в одной транзакции из сервиса
после блокировки строки таблицы SELECT FOR UPDATE
коннекция хранится в ContextVar
"""


@asynccontextmanager
async def begin_transaction(db_engine):
    async with db_engine.acquire() as conn:
        async with conn.begin():
            conn_context = connection.set(conn)
            try:
                yield
            finally:
                connection.reset(conn_context)


class _TransactionContextManager:

    def __init__(self, db_engine):
        self.db_engine = db_engine
        self.db_connection: SAConnection = None
        self.transaction: Transaction = None

    async def __aenter__(self):
        self.db_connection = await self.db_engine.acquire()
        self.transaction = await self.db_connection.begin()
        self.connection_context = connection.set(self.db_connection)
        # return self

    async def __aexit__(self, exc_type, exc, tb):
        if exc_type:
            await self.transaction.rollback()
        else:
            if self.transaction.is_active:
                await self.transaction.commit()

        # можно и закрывать т.к. метод обертки SAConnection вызывается
        # а исходная коннекция все равно возвращается в пул, а не закрывается
        # await self.db_connection.close()

        connection.reset(self.connection_context)
        await self.db_engine.release(self.db_connection)

        self.db_connection = None
        self.transaction = None
        self.connection_context = None
