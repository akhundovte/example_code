import json

from lxml import html

from ...exceptions import ParseError
from ...base_parser import BaseParser


class Parser(BaseParser):
    shop_name = 'zara'
    color_key = 'v1'
    key_json = 'window.zara.viewPayload'

    def _prepare_params(self, url: str, params):
        """ """
        index = url.rfind('?')
        if index != -1:
            url_parse = url[:index]
        else:
            url_parse = url
        params['url_parse'] = url_parse
        return url_parse

    def get_jsondata_from_html(self, content):
        tree = html.fromstring(content)
        scripts_find = tree.xpath("//script[@type='text/javascript']/text()")

        script_text = None
        for item in scripts_find:
            idx = item.find(self.key_json)
            if idx == -1:
                continue
            cut_script_text = item[idx+len(self.key_json):]
            idx_open_bkt = cut_script_text.find("{")

            if idx_open_bkt != -1:
                script_text = cut_script_text[idx_open_bkt:-1]
                break
        if not script_text:
            raise ParseError('not find key_json')

        return json.loads(script_text)

    def _parse(self, content, **params):
        """
        не возвращаем selected т.к. при смене цветов на странице товара
        параметр v1 не меняется
        """
        url_parse = params.get('url_parse')

        data = self.get_jsondata_from_html(content)

        product = data['product']
        name = product['name']
        # product['detail']['reference']
        reference = product['detail']['displayReference']

        if not product['isBuyable']:
            self.warning_msgs.append("Параметр isBuyable == False")

        price_product = product['price']

        stocks = []
        types = []
        colors = product['detail']['colors']
        for color in colors:
            name_color = color['name']
            code_color = color['id']
            # указывается в параметрах запроса
            product_id_color = color['productId']
            price_color = color['price']
            price_old_color = color.get('oldPrice')

            if price_product != price_color:
                msg = (f"разная стоимость для товара и цвета {code_color}"
                       f"{price_product} {price_color}")
                self.warning_msgs.append(msg)
            try:
                price_sale = price_color / 100
            except (ValueError, TypeError):
                raise ParseError('price invalid')

            if price_old_color is None:
                price_base = price_sale
            else:
                try:
                    price_base = price_old_color / 100
                except (ValueError, TypeError):
                    raise ParseError('price old invalid')

            sizes = color['sizes']
            for size in sizes:
                availability = size['availability']
                size_name = size['name']
                size_code = str(size['id'])

                if availability == 'in_stock':
                    size_available = True
                elif availability == 'out_of_stock':
                    size_available = False
                elif availability == 'coming_soon':
                    size_available = False
                elif availability == 'back_soon':
                    size_available = False
                else:
                    raise ParseError('availability invalid')

                if price_color != size['price']:
                    msg = (f"разная стоимость для товара и размера {size_name}"
                           f"{price_color} {size['price']}")
                    self.warning_msgs.append(msg)

                stocks.append({
                    'sku': str(size['sku']), 'available': size_available,
                    'price_base': price_base, 'price_sale': price_sale,
                    'parameters': {
                        'type_code': code_color,
                        'option_code': size_code, 'option_name': size_name
                        },
                    })

            types.append({
                'code': code_color,
                'name': name_color,
                'url': '%s?%s=%s' % (url_parse, self.color_key, product_id_color),
                })

        product_data = {
            'reference': reference,
            'name': name,
            'url': url_parse,
            'url_parse': url_parse,
            'parameters': {
                'types': types
                },
            'stocks': stocks
            }
        return {
            'data': product_data,
            }
