from decimal import Decimal
from lxml import html

from ...base_parser import BaseParser
from ...exceptions import ParseError


class Parser(BaseParser):
    shop_name = 'rivegauche'

    def _parse(self, content, **params):
        url = params.get('url_parse')
        tree = html.fromstring(content)
        product_data = self._parse_content(tree, url)
        return {'data': product_data}

    def _parse_content(self, tree, url):
        product_content_nodes = tree.cssselect("div.product-content")[0]

        id_text = product_content_nodes.cssselect("div.product-code")[0].text

        idx = id_text.find("ID:")
        if idx != -1:
            reference = id_text[idx+3:].strip()
        else:
            raise ParseError('не найден ID в dom')

        product_titles = product_content_nodes.cssselect("div.product-titles__desktop")[0]

        product_name = product_titles.xpath("//h1/text()")[0].strip()
        type_name = product_titles.xpath("div[@class='product-subtitle']/text()")[0].strip()

        price_base = None
        price_sale = None
        price_card = None
        price_group = product_content_nodes.cssselect("div.product-price-group div.price")

        if len(price_group) == 1:
            price_group_item = price_group[0]
            price_base = price_group_item.attrib['content']
            price_old = price_group_item.cssselect("div.price-old")
            if price_old:
                # price_sale_text = price_group_item.xpath("span/text()")[0]
                # price_sale = ''.join(price_sale_text.split())
                price_sale_text = price_group_item.xpath("meta")[0]
                price_sale = price_sale_text.attrib['content']
        elif len(price_group) == 2:
            price_card = Decimal(price_group[0].attrib['content'])
            price_base = Decimal(price_group[1].attrib['content'])
            if price_card > price_base:
                raise ParseError('цена по карте больше базовой цены')
        else:
            raise ParseError('количество элементов в price_group не соответствует предполагаемому')

        available = True
        buttons = product_content_nodes.cssselect("div.product-action button")
        if len(buttons) == 2:
            if 'disabled' in buttons[0].attrib and 'disabled' in buttons[1].attrib:
                available = False
        else:
            raise ParseError('количество элементов в product-action не соответствует предполагаемому')

        product_stock = {
            'sku': reference,
            'available': available,
            'price_base': price_base,
            'price_sale': price_sale,
            'price_card': price_card,
            }

        product_data = {
            'name': f"{product_name} {type_name}",
            'url': url,
            'url_parse': url,
            'reference': reference,
            'stocks': [product_stock, ]
            }

        return product_data
