import asyncio
import aiohttp

from .exceptions import (
    HttpError, ConnectionRequestError, ConnectionTimeout,
    HTTPResponseError, HTTPResponseEntityTooLarge, ConnectionRetryError
    )


from apps.shopwatcher.management import send_msg_admins

# по умолчанию и в библиотеке 5 мин
TIMEOUT = 5 * 60
DEFAULT_CHUNK_SIZE = 64 * 2**10
# 50 Mb = 50 * 2**10 * 2**10 = 50 * 1024 * 1024 = 52428800
RESPONSE_MAX_BYTES = 30 * 2**10 * 2**10


class ConnectionAioHttp:
    """
    Обертка над aiohttp.ClientSession
    кое-что взято из elasticsearch.py класс Transport() и aioelasticsearch - connection.py

    Организовано повторение запроса в случае ошибки
    """

    def __init__(self, timeout=None, max_retries=3, retry_on_status=(502, 503, 504, )):
        """
        retry_on_status
            502 Bad Gateway («плохой, ошибочный шлюз»)
            503 Service Unavailable («сервис недоступен»)
            504 Gateway Timeout («шлюз не отвечает»)
        """
        if timeout is None:
            timeout = aiohttp.ClientTimeout(total=TIMEOUT, connect=None, sock_read=None)
        self.max_retries = max_retries
        self.retry_on_status = retry_on_status
        # сессия создастся с TCPConnector -> по умолчанию limit=100 - кол-во соединений
        self.session = aiohttp.ClientSession(timeout=timeout)

    async def perform_request(self, url, method='GET', **kwargs):
        """
        """
        for attempt in range(self.max_retries + 1):
            if attempt > 0:
                msg = f"Попытка номер {attempt} для {url}"
                await send_msg_admins(msg)
            try:
                # add a delay before attempting the next retry
                # 0, 1, 3, 7, etc...
                delay = 2**attempt - 1
                await asyncio.sleep(delay)
                resp_data = await self.request(url, method, **kwargs)
            except HttpError as e:
                retry = False
                if isinstance(e, (ConnectionRetryError, ConnectionTimeout)):
                    retry = True
                elif isinstance(e, HTTPResponseError) and e.status_code in self.retry_on_status:
                    retry = True
                if retry:
                    if attempt == self.max_retries:
                        raise e
                else:
                    raise e
            else:  # если исключения не было
                return resp_data

    async def request(self, url, method, **kwargs) -> bytes:
        """
        возвращает словарь ответа (преобразованный из json)

        на примере elesticsearch.py retry будем делать в случае ошибок
            ConnectionRequestError, ServerResponseError(502, 503, 504),
            ConnectionTimeout(хотя по умолчанию в elastic по ней нет повторного запроса)
        """
        raw_data = None
        chunk_size = DEFAULT_CHUNK_SIZE
        max_size = RESPONSE_MAX_BYTES
        try:
            async with self.session.request(method, url, **kwargs) as response:
                if 400 <= response.status < 500:
                    http_error_msg = '%s Client Error for url: %s' % (response.status, url)
                    raise HTTPResponseError(http_error_msg, status_code=response.status)

                elif 500 <= response.status < 600:
                    http_error_msg = '%s Server Error for url: %s' % (response.status, url)
                    raise HTTPResponseError(http_error_msg, status_code=response.status)

                # аналогия серверной части aiohttp - web_request.py - BaseRequest.read()
                # сделал так чтобы ограничить размер скачанных данных
                # в оригинальной read() этого нет, НО есть обработка ошибок см. - aiohttp\client_reqrep.py
                # https://docs.aiohttp.org/en/stable/client_quickstart.html#streaming-response-content
                body = bytearray()
                size = 0
                while True:
                    chunk = await response.content.read(chunk_size)
                    if not chunk:
                        break
                    body.extend(chunk)
                    size += len(chunk)
                    if 0 < max_size < size:
                        msg = 'Maximum body size {} exceeded, actual size {}'\
                            .format(max_size, size)
                        raise HTTPResponseEntityTooLarge(msg)

                raw_data = bytes(body)

        except Exception as e:
            if isinstance(e, HttpError):  # наше базовое исключение
                raise e
            # на TimeoutError реагируем повторными запросами
            if isinstance(e, asyncio.TimeoutError):
                raise ConnectionTimeout('TIMEOUT %s' % str(e), error=e)
            # на данные ошибки реагируем повторными запросами
            if isinstance(e, (aiohttp.ServerConnectionError, aiohttp.ClientPayloadError)):
                str_error = str(e)
                if hasattr(e, 'message') and e.message is None:
                    str_error = str(type(e))
                raise ConnectionRetryError(str_error, error=e)
            # базовая ошибка aiohttp - на все остальные ошибки без retry
            if isinstance(e, aiohttp.ClientError):
                str_error = str(e)
                raise ConnectionRequestError(str_error, error=e)
            raise e
        return raw_data

    async def close(self):
        await self.session.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
