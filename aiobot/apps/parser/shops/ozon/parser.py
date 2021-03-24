import json

from decimal import Decimal
from lxml import html

from ...exceptions import ParseError
from ...base_parser import BaseParser


class Parser(BaseParser):
    shop_name = 'ozon'

    def _parse(self, content, **params):
        tree = html.fromstring(content)
        el = tree.xpath("//div[starts-with(@id, 'state-webAddToCart')]")
        if not el:
            raise ParseError('На странице не найден основной элемент DOM, '
                             f'размер контента {len(content)} символов')

        data_json = el[0].attrib['data-state']
        data = json.loads(data_json)

        product_info = data['cellTrackingInfo']['product']

        orig_id = str(product_info['id'])
        title = product_info['title']
        url = product_info['link']

        price_base = Decimal(product_info['price'])
        price_sale = Decimal(product_info['finalPrice'])

        stocks = [{
            'sku': str(data['sku']), 'available': data['isAvailable'],
            'price_base': price_base, 'price_sale': price_sale,
            }, ]

        product_data = {
            'name': title,
            'url': url,
            'url_parse': url,
            'reference': orig_id,
            'stocks': stocks,
            }

        return {
            'data': product_data,
            }
