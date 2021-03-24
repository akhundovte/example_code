import asyncio
import traceback

from .connection import ConnectionAioHttp
from .exceptions import HttpError, ConsumerError


class AdapterAioHttp(object):
    """
    """
    def __init__(self,
                 handler_response=None,
                 handler_errors=None,
                 queue_size=100,
                 count_consumer=1):
        self.queue_size = queue_size
        self.count_consumer = count_consumer
        self.handler_response = handler_response
        self.handler_errors = handler_errors
        self._connector = ConnectionAioHttp()

    def get_connector(self):
        return self._connector

    async def single_request(self, url, **kwargs):
        async with self._connector as connector:
            return await connector.perform_request(url, **kwargs)

    async def queue_request(self, params_iter):
        queue = asyncio.Queue(maxsize=self.queue_size)
        async with self._connector as connector:
            # schedule the consumer - задачи теперь в цикле событий в ожидании
            consumers = [asyncio.create_task(self.consumer(queue=queue,
                                                           connector=connector
                                                           )) for _ in range(self.count_consumer)]
            producer = asyncio.create_task(self.produce(queue=queue, params_iter=params_iter))
            done, pending = await asyncio.wait([producer, *consumers],
                                               return_when=asyncio.FIRST_COMPLETED)

            queue_complete = None
            if producer in done:
                queue_complete = asyncio.create_task(queue.join())
                await asyncio.wait([queue_complete, *consumers],
                                   return_when=asyncio.FIRST_COMPLETED)
            else:
                await _cancel_task(producer)

        if queue_complete and not queue_complete.done():
            await _cancel_task(queue_complete)

        errors = []
        for consumer_future in consumers:
            await _cancel_task(consumer_future)
            if consumer_future.cancelled():
                continue
            if consumer_future.exception() is not None:
                errors.append(consumer_future.exception())

        if errors:
            return {'errors': errors}
        return {'result': 'success'}

    async def produce(self, queue, params_iter):
        """
        Производитель - кладет параметры запроса в очередь
        """
        for item in params_iter:
            await queue.put(item)
            await asyncio.sleep(2)

    async def consumer(self, queue, connector):
        """
        Потребитель - забирает из очереди параметры запроса и совершает запрос
        """
        try:
            while True:
                kwargs = await queue.get()
                try:
                    url = kwargs.get('url')
                    params = kwargs.get('params')
                    auth = kwargs.get('auth')
                    headers = kwargs.get('headers')
                    cookies = kwargs.get('cookies')
                    kwargs_handler = kwargs.get('kwargs')
                    response = await connector.perform_request(url=url, params=params, auth=auth,
                                                               headers=headers, cookies=cookies)
                    if self.handler_response is not None:
                        if kwargs_handler is None:
                            kwargs_handler = {'url': url}

                        if asyncio.iscoroutinefunction(self.handler_response):
                            second_request = kwargs_handler.get('second_request', False)

                            if second_request:
                                kwargs_handler['connector'] = connector
                            await self.handler_response(response, **kwargs_handler)
                        else:
                            self.handler_response(response, **kwargs_handler)
                except HttpError as e:
                    if self.handler_errors is not None:
                        if asyncio.iscoroutinefunction(self.handler_response):
                            result = await self.handler_errors(e, **kwargs)
                        else:
                            result = self.handler_errors(e, **kwargs)
                        if not result:
                            raise e
                    else:
                        raise e

                queue.task_done()

        except Exception as e:
            if isinstance(e, asyncio.CancelledError):
                pass
            else:
                tb = traceback.format_exc()
                msg_traceback = f"....\nOriginal exception was:\n {tb}"
                msg_exc = (
                    f"Ошибка в функции consumer:\nurl: {url}\nтип ошибки: {type(e)}\n"
                    f"текст ошибки: {str(e)} \n{msg_traceback}"
                    )
                raise ConsumerError(msg_exc)


async def _cancel_task(task):
    if task.done():
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
