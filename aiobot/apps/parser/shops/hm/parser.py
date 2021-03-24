import json

from lxml import html


from utils.client_async import AdapterAioHttp, ConnectionAioHttp

from ...exceptions import ParseError
from ...utils import get_text_from_area, get_host_from_url
from ...base_parser import BaseParser


class Parser(BaseParser):
    shop_name = 'hm'
    key_json = 'productArticleDetails'
    url_available_template = "%s/hmwebservices/service/product/ru/availability/%s.json"

    async def get_response_and_parse(self, url: str, **kwargs):
        """Вызывается в views.py
        """
        adapter = AdapterAioHttp()
        headers = kwargs.get('headers')

        _connector = adapter.get_connector()
        async with _connector as connector:
            response_raw = await connector.perform_request(url=url, headers=headers)
            return await self.parse_response(data_raw=response_raw,
                                             connector=connector,
                                             url_parse=url,
                                             headers=headers,
                                             )

    async def parse_response(self,
                             data_raw: bytes,
                             connector: ConnectionAioHttp,
                             **kwargs):
        """Вызывается в tasks.py и из self.get_response_and_parse()
        уникально тем, что есть второй запрос после обработки результатов первого
        """
        response_data = data_raw.decode(encoding='utf-8')
        headers = kwargs.get('headers')
        try:
            url_available, product_data, color_selected = self._parse(response_data, **kwargs)
            # async with connector as _connector:
            response_raw = await connector.perform_request(url=url_available, headers=headers)
            parse_result = self._parse_second(response_raw.decode(encoding='utf-8'),
                                              product_data, color_selected)
        except (LookupError, TypeError, ValueError, ParseError) as e:  # LookupError parent of IndexError, KeyError
            raise ParseError(f"Парсер {self.shop_name} - ошибка {type(e)}: {str(e)}")

        await self.check_and_send_warnings(parse_result['data']['reference'])
        return parse_result

    def _parse(self, content, **kwargs):
        url_parse = kwargs.get('url_parse')
        host = get_host_from_url(url_parse)

        tree = html.fromstring(content)

        product_name = tree.xpath("//section[@class='name-price']/h1/text()")[0].strip()

        scripts_find = tree.xpath("//script")
        script_text = None
        for script in scripts_find:
            script_text = script.text
            if script_text:
                product_code = get_text_from_area(script_text, 'ancestorProductCode',
                                                  open_sym="'", close_sym="'", with_sym=False)
                if product_code is not None:
                    break
        if not script_text:
            raise ParseError("")

        data = self.get_json_from_dom(script_text)
        color_selected = data['articleCode']

        types = []
        stocks_size = []
        for color_key, value in data.items():
            if product_code in color_key:
                color_name = value['name']
                # code = value['colorCode']
                sizes = value['sizes']
                price_base = value['whitePriceValue']
                price_sale = value.get('redPriceValue')
                # soon = value['comingSoon']
                color_url = value['url']
                for size in sizes:
                    sku = size['sizeCode']
                    stocks_size.append({
                        'sku': sku,
                        'price_base': price_base, 'price_sale': price_sale,
                        'parameters': {
                            'type_code': color_key,
                            'option_name': size['name'],
                            'option_code': size['size'],
                            }
                        })
                types.append({
                    'code': color_key,
                    'name': color_name,
                    'url': f"{host}{color_url}",
                    })

        product_data = {
            'reference': product_code,
            'name': product_name,
            'url': None,
            'url_parse': types[0]['url'],
            'stocks': stocks_size,
            'parameters': {
                'type_label': 'Цвет',
                'option_label': 'Размер',
                'types': types,
                }
            }

        url_available = self.url_available_template % (host, product_code)
        return url_available, product_data, color_selected

    def get_json_from_dom(self, script_text):
        data_text = get_text_from_area(script_text, self.key_json)
        data_text = data_text.replace("\'", "\"")
        data_text = data_text.replace('\t', '')
        data_text = data_text.replace('\n', '')

        idx = data_text.find(' ? ')
        while idx != -1:
            idx1 = data_text[:idx].rfind('{')
            idx2 = data_text[idx:].find('}')
            data_text = data_text[:idx1+1] + data_text[idx+idx2:]
            idx = data_text.find(' ? ')
        return json.loads(data_text)

    def _parse_second(self, content, product_data, color_selected):
        data_api = json.loads(content)

        availability = set(data_api['availability'])
        for stock in product_data['stocks']:
            if stock['sku'] in availability:
                stock['available'] = True
            else:
                stock['available'] = False

        return {
            'data': product_data,  # dict
            'selected': color_selected,  # str
            }
