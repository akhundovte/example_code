import json

from decimal import Decimal

from urllib.parse import urlparse

from utils.client_async import AdapterAioHttp, ConnectionAioHttp

from ...exceptions import ParseError
from ...utils import get_jsondata_from_html, get_text_from_area
from ...base_parser import BaseParser

# добавилось keyStoreDataversion, поэтому ищем ссылку на странице товара
# url_api_template = 'https://www.asos.com/api/product/catalogue/v3/stockprice?productIds=%s&store=RU&currency=RUB'


class Parser(BaseParser):
    shop_name = 'asos'
    key_json = 'window.asos.pdp.config.product'
    # key_api = 'window.asos.pdp.stockApiRequest'
    key_api = 'window.asos.pdp.config.stockPriceApiUrl'

    async def get_response_and_parse(self, url: str, **kwargs):
        """Вызывается в views.py
        """
        adapter = AdapterAioHttp()
        headers = kwargs.get('headers')
        cookies = kwargs.get('cookies')

        index = url.rfind('?')
        if index != -1:
            url_parse = url[:index]
        else:
            url_parse = url

        _connector = adapter.get_connector()
        async with _connector as connector:
            response_raw = await connector.perform_request(url=url, headers=headers, cookies=cookies)
            return await self.parse_response(data_raw=response_raw,
                                             connector=connector,
                                             url_parse=url_parse,
                                             headers=headers,
                                             cookies=cookies)

    async def parse_response(self,
                             data_raw: bytes,
                             connector: ConnectionAioHttp,
                             **kwargs):
        """Вызывается в tasks.py и из self.get_response_and_parse()
        уникально тем, что есть второй запрос после обработки результатов первого
        """
        response_data = data_raw.decode(encoding='utf-8')
        headers = kwargs.get('headers')
        cookies = kwargs.get('cookies')
        try:
            url_api, product_data, sizes_const = self._parse(response_data, **kwargs)
            # async with connector as _connector:
            response_raw = await connector.perform_request(url=url_api, headers=headers, cookies=cookies)
            parse_result = self._parse_second(response_raw.decode(encoding='utf-8'),
                                              product_data, sizes_const)
        except (LookupError, TypeError, ValueError, ParseError) as e:  # LookupError parent of IndexError, KeyError
            raise ParseError(f"Парсер {self.shop_name} - ошибка {type(e)}: {str(e)}")

        await self.check_and_send_warnings(parse_result['data']['reference'])
        return parse_result

    def _parse(self, content, **kwargs):
        url_parse = kwargs.get('url_parse')

        url_struct = urlparse(url_parse)
        host = '%s://%s' % (url_struct.scheme, url_struct.netloc)

        url_api = None
        idx_api = content.find(self.key_api)
        if idx_api != -1:
            url_api = host + get_text_from_area(
                text=content[idx_api:], key='=',
                open_sym="\'", close_sym="\';",
                with_sym=False
                )
            # url_api = host + get_text_from_area(
            #     text=content[idx_api:], key='fetch',
            #     open_sym="\"", close_sym="\"",
            #     with_sym=False
            #     )

        data = get_jsondata_from_html(content, self.key_json, set_type_script=True)

        sizes_const = {}
        # раньше для формирования ссылки api использовался
        # product_id = data['id']
        variants = data['variants']
        color_name = variants[0]['colour']
        color_code = variants[0]['colourWayId']

        product_data = {
            'url': url_parse,
            'url_parse': url_parse,
            'name': data['name'],
            'reference': data['productCode'],
            }
        # варианты - это разные размеры
        for variant in variants:
            if color_name != variant['colour']:
                msg = f"Цвет товара отличается от цвета variant - {color_name} и {variant['colour']}"
                self.warning_msgs.append(msg)
            if color_code != variant['colourWayId']:
                msg = f"Id цвета товара отличается от id цвета variant - {color_code} и {variant['colourWayId']}"
                self.warning_msgs.append(msg)
            sizes_const[variant['variantId']] = {
                'option_name': variant['size'], 'option_code': str(variant['sizeId'])
                }

        return url_api, product_data, sizes_const

    def _parse_second(self, content, product_data, sizes_const):
        data_api = json.loads(content)

        if len(data_api) > 1:
            self.warning_msgs.append("в списке более одного продукта")

        product = data_api[0]
        # price_struct_product = product['productPrice']
        # price_sale_product = Decimal(price_struct_product['current']['value'])
        # price_product = Decimal(price_struct_product['previous']['value'])

        stocks_size = []
        for variant in product['variants']:
            parameters = sizes_const[variant['variantId']]
            price_struct_var = variant['price']
            price_sale = Decimal(price_struct_var['current']['value'])
            price_base = Decimal(price_struct_var['previous']['value'])
            stock = {
                'sku': str(variant['variantId']), 'available': variant['isInStock'],
                'price_sale': price_sale, 'price_base': price_base,
                'parameters': parameters
                }
            stocks_size.append(stock)
        product_data['stocks'] = stocks_size

        return {
            'data': product_data,  # dict
            }
