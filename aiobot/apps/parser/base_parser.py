from apps.shopwatcher.management import send_msg_admins

from decimal import InvalidOperation

from utils.client_async import AdapterAioHttp

from .exceptions import ParseError


class BaseParser:

    shop_name = None

    def __init__(self):
        self.warning_msgs = []

    async def get_response_and_parse(self, url: str, **kwargs):
        """Вызывается в views.py
        """
        adapter = AdapterAioHttp()
        headers = kwargs.get('headers')
        cookies = kwargs.get('cookies')
        params: dict = {'url_parse': url}
        if hasattr(self, '_prepare_params'):
            url = self._prepare_params(url, params)

        response_data_raw = await adapter.single_request(url=url, headers=headers, cookies=cookies)
        return await self.parse_response(response_data_raw, **params)

    async def parse_response(self, data_raw: bytes, **params):
        """Вызывается в tasks.py и из get_response_and_parse()"""
        try:
            response_data = data_raw.decode(encoding='utf-8')
            parse_result = self._parse(response_data, **params)
        except (LookupError, TypeError, ValueError, InvalidOperation, ParseError) as e:
            # LookupError parent of IndexError, KeyError
            raise ParseError(f"Парсер {self.shop_name} - ошибка {type(e)}: {str(e)}")

        await self.check_and_send_warnings(params.get('url_parse'))
        return parse_result

    async def check_and_send_warnings(self, url):
        if self.warning_msgs:
            msg = f"Парсер {self.shop_name}: url - {url}\n"
            msg += '\n'.join(self.warning_msgs)
            await send_msg_admins(msg)

    def _parse(self, content, **params):
        raise NotImplementedError()
