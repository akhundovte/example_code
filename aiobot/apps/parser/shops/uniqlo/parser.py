import json

from urllib.parse import urlparse, parse_qsl

from utils.client_async import AdapterAioHttp, ConnectionAioHttp

from ...exceptions import ParseError
from ...base_parser import BaseParser


class Parser(BaseParser):
    shop_name = 'uniqlo'
    url_product_tmplt = 'https://www.uniqlo.com/ru/estore/ru_RU/product-detail.html?productCode=%s'
    url_descr_tmplt = 'https://www.uniqlo.com/ru/estore/data/products/spu/ru_RU/%s.json'
    url_price_tmplt = 'https://d.uniqlo.com/ru/estore/product/i/product/spu/pc/query/%s/ru_RU'
    url_stock = 'https://d.uniqlo.com/ru/estore/stock/stock/query/ru_RU'

    async def get_response_and_parse(self, url: str, **kwargs):
        """Вызывается в views.py
        """
        adapter = AdapterAioHttp()
        connector = adapter.get_connector()
        headers = kwargs.get('headers')
        params = self._prepare_params(url)

        async with connector as _connector:
            response_raw = await _connector.perform_request(
                url=params['url_parse'], headers=headers
                )
            return await self.parse_response(
                response_raw,
                connector=_connector,
                headers=headers, **params
                )

    def _prepare_params(self, url: str):
        """ """
        url_struct = urlparse(url)
        qparams = dict(parse_qsl(url_struct.query))
        product_code = qparams.get('productCode')
        if product_code is None:
            product_code = qparams.get('pid')
        type_selected = qparams.get('colorNo')

        # url_product = ('%s://%s%s?productCode=%s' %
        #                (url_struct.scheme, url_struct.netloc, url_struct.path, product_code)
        #                )

        if not product_code:
            raise ParseError('не удается выделить из ссылки productCode')

        params = {
            'url_parse': self.url_descr_tmplt % product_code,
            'url_product': self.url_product_tmplt % product_code,
            'selected': type_selected,
            }
        return params

    async def parse_response(self,
                             response_raw: bytes,
                             connector: ConnectionAioHttp,
                             **kwargs):
        """
        Вызывается в tasks.py и из self.get_response_and_parse()
        уникально тем, что есть второй запрос после обработки результатов первого
        """
        selected = kwargs.get('selected')
        response_data = response_raw.decode(encoding='utf-8')
        try:
            product_data, sku_data, product_code = self._parse_desc(response_data, **kwargs)
            headers = kwargs.get('headers')
            response_raw = await connector.perform_request(
                url=self.url_price_tmplt % product_code, headers=headers
                )
            self._parse_price(response_raw.decode(encoding='utf-8'), sku_data)

            json_payload = {
                'distribution': "EXPRESS",
                'productCode': product_code,
                'type': "DETAIL",
                }
            response_raw = await connector.perform_request(url=self.url_stock, method="POST",
                                                           headers=headers, json=json_payload)
            self._parse_stock(response_raw.decode(encoding='utf-8'), sku_data)

            product_data['stocks'] = list(sku_data.values())
            parse_result = {'data': product_data, 'selected': selected}

        except (LookupError, TypeError, ValueError, ParseError) as e:  # LookupError parent of IndexError, KeyError
            raise ParseError(f"Парсер {self.shop_name} - ошибка {type(e)}: {str(e)}")

        await self.check_and_send_warnings(parse_result['data']['reference'])
        return parse_result

    def _parse_desc(self, content, **kwargs):
        url_parse = kwargs.get('url_parse')
        url_product = kwargs.get('url_product')
        url_type_tmplt = url_product + '&colorNo={color_code}'

        data = json.loads(content)

        summary = data['summary']
        product_data = {
            'reference': summary['code'],
            'name': summary['fullName'],
            'url': url_product,
            'url_parse': url_parse,
            }

        types = []
        code_uniq = set()
        sku_data = {}
        for item in data['rows']:
            type_name = item['styleText']
            type_code = item['colorNo']
            if type_code not in code_uniq:
                types.append({
                    'code': type_code,
                    'name': type_name,
                    'url': url_type_tmplt.format(color_code=type_code)
                    })
                code_uniq.add(type_code)
            sku_data[item['productId']] = {
                'sku': str(item['skuId']),
                'parameters': {
                    'type_code': type_code,
                    'option_name': item['sizeText'],
                    'option_code': item['sizeNo'],
                    }
                }

        product_data['parameters'] = {
            'type_label': 'Цвет',
            'option_label': 'Размер',
            'types': types,
            }
        product_code = summary['productCode']
        return product_data, sku_data, product_code

    def _parse_price(self, content, sku_data):
        data = json.loads(content)

        if len(data['resp']) > 1:
            msg = "_parse_price количество элементов больше 1"
            self.warning_msgs.append(msg)

        data_resp = data['resp'][0]

        price = data_resp['summary']['originPrice']
        for item in data_resp['rows']:
            product_item = sku_data.get(item['productId'])
            if not product_item:
                continue
            product_item['price_sale'] = item['price']
            product_item['price_base'] = price

    def _parse_stock(self, content, sku_data):
        data = json.loads(content)

        if len(data['resp']) > 1:
            msg = "_parse_stock количество элементов больше 1"
            self.warning_msgs.append(msg)

        # skuStocks - забрать в магазине
        # expressSkuStocks - доставка

        # if data['resp'][0]['skuStocks'] != data['resp'][0]['expressSkuStocks']:
        #     msg = "skuStocks != expressSkuStocks"
        #     self.warning_msgs.append(msg)

        for product_id, qty in data['resp'][0]['expressSkuStocks'].items():
            sku_data[product_id]['available'] = bool(qty)
