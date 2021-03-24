

class BaseDBEngine:
    def __init__(self):
        self._engine = None

    @property
    def engine(self):
        if self._engine is None:
            raise ValueError('Call create method before get engine attr')
        return self._engine

    async def create(self, conn_params):
        self._engine = await self.get_new_engine(conn_params)

    async def get_new_engine(self, conn_params):
        """Open a connection to the database."""
        raise NotImplementedError(
            'subclasses of BaseDatabaseWrapper may require a get_new_connection() method'
            )

    async def close(self):
        if self._engine is not None:
            self._engine.close()
            await self._engine.wait_closed()
