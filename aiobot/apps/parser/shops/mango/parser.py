import json
import re

from urllib.parse import urlparse, parse_qsl

from ...exceptions import ParseError
from ...base_parser import BaseParser


class Parser(BaseParser):
    shop_name = 'mango'
    color_key = 'c'
    template_url = 'https://shop.mango.com/services/garments/%s'

    def _prepare_params(self, url: str, params):
        """ """
        url_struct = urlparse(url)
        color_selected = None
        if url_struct.query:
            query_dict = dict(parse_qsl(url_struct.query))
            color_selected = query_dict.get(self.color_key)

        index = url.rfind('?')
        if index != -1:
            url_product = url[:index]
        else:
            url_product = url

        reference = url_struct.path.rpartition('_')[2].rpartition('.')[0]
        url_parse = self.template_url % (reference)
        params['color_selected'] = color_selected
        params['url_parse'] = url_parse
        params['url_product'] = url_product
        return url_parse

    def _parse(self, content, **params):
        """ """
        data = json.loads(content)

        url_parse = params.get('url_parse')
        url_product = params.get('url_product')
        color_selected = params.get('color_selected')

        # проблемы возникают, меняется с русского на английский иногда
        # url_canonical = 'https://shop.mango.com%s' % data['canonicalUrl']
        garment_id = data['id']
        colors = data['colors']['colors']
        stocks = []
        types = []
        for color in colors:
            # есть проблема на некоторых товарах с цветом, поэтому лучше пропустить
            if 'sizes' not in color:
                continue
            code_color = color['id']
            name_color = color['label']
            price_base = price_sale = None
            price_struct = color.get('price')
            if price_struct:
                price_sale = price_struct.get('price')
                if price_sale:
                    price_sale = int(price_sale)

                crossed_prices = price_struct.get('crossedOutPrices')
                if crossed_prices:
                    if len(crossed_prices) > 1:
                        msg = f"для {code_color} по ключу crossedOutPrices более одного элемента"
                        self.warning_msgs.append(msg)
                    price_str = crossed_prices[0]
                    price_base = int(''.join(re.findall(r'(\d+)', price_str)))
                else:
                    price_base = price_sale
            for size in color['sizes']:
                size_name = size['value']
                size_code = size['id']
                if size_code == '-1':  # это пункт выберите размер
                    continue
                size_available = size.get('available', False)

                # garmentId=67070518&colorId=56&sizeId=21
                sku = f"{garment_id}-{code_color}-{size_code}"
                stocks.append({
                    'sku': sku, 'available': size_available,
                    'price_sale': price_sale, 'price_base': price_base,
                    'parameters': {
                        'type_code': code_color,
                        'option_code': size_code,
                        'option_name': size_name,
                        }
                    })
            types.append({
                'code': code_color,
                'name': name_color,
                'url': '%s?%s=%s' % (url_product, self.color_key, code_color),
                })

        # т.к. отсутствия ключа sizes сделал допустимым из-за проблемы с цветами
        # то надо ловить такую ситуацию
        if not types:
            raise ParseError('types is empty')

        product_data = {
            'reference': data['id'],
            'name': data['name'],
            'url': url_product,
            'url_parse': url_parse,
            'parameters': {
                'types': types,
                },
            'stocks': stocks,
            }

        return {
            'data': product_data,  # dict
            'selected': color_selected,  # str
            }
