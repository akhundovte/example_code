from lxml import html
from decimal import Decimal

from ...base_parser import BaseParser


class Parser(BaseParser):
    shop_name = 'henderson'

    def _parse(self, content, **kwargs):
        url_parse = kwargs.get('url_parse')
        tree = html.fromstring(content)
        product_data = self._get_product_data(tree, url_parse)
        return {'data': product_data}

    def _get_product_data(self, tree, url_parse):

        product_content = tree.cssselect("div.product-container__right")[0]
        product_name = product_content.xpath("//h1[@class='ttl']/text()")[0]
        product_main = product_content.xpath("//div[@id='MC']")[0]

        # product_main.attrib['data-id']
        # reference = product_main.attrib['data-modelcode']
        reference_color = product_main.text.replace(' ', '-')

        price_base, price_sale = self._get_price(product_content)
        stocks = self._get_stocks(product_content, price_base, price_sale)

        product_data = {
            'name': product_name,
            'url': url_parse,
            'url_parse': url_parse,
            'reference': reference_color,
            'stocks': stocks
            }
        return product_data

    def _get_price(self, product_content):
        prices = product_content.cssselect("div.pp_prices")[0]

        price_base = None
        price_sale = None

        price_t = prices.xpath("//div[@class='pp_price']/text()")[0]
        price_sale = Decimal(''.join(price_t.split()))

        price_old = prices.xpath("//div[@class='pp_price_old']/text()")
        if price_old:
            price_base = Decimal(''.join(price_old[0].split()))
        else:
            price_base = price_sale
        return price_base, price_sale

    def _get_stocks(self, product_content, price_base, price_sale):
        sizes = product_content.cssselect("div.sizes-header__left")[0]
        sizes_option = sizes.cssselect("select.js-size-product option")

        button_available = product_content.cssselect("div.wrap-btns span.wrap-btns__info")[0]
        if 'd-none' in button_available.attrib['class']:
            available_global = True
        else:
            available_global = False

        stocks = []
        if not sizes_option:
            sizes_none = sizes.cssselect("div.no-size")
            if not sizes_none:
                msg = "нет div.no-size"
                self.warning_msgs.append(msg)
            else:
                sku = sizes_none[0].attrib['data-value']
                stock_item = {
                    'sku': sku, 'available': available_global,
                    'price_sale': price_sale, 'price_base': price_base
                    }
                stocks.append(stock_item)
        else:
            sizes_available = []
            for item in sizes_option:
                val = item.attrib['value']
                if not val:
                    continue
                sku = item.get('data-id')
                disabled = item.get('disabled')
                if disabled is None:
                    available = True
                else:
                    available = False
                stock_item = {
                    'sku': sku, 'available': available,
                    'price_sale': price_sale, 'price_base': price_base,
                    'parameters': {'option_name': val, 'option_code': val}
                    }
                stocks.append(stock_item)
                sizes_available.append(available)

            if sizes_available:
                if ((available_global and not any(sizes_available)) or
                        (not available_global and any(sizes_available))):
                    msg = "available_global не соответствует доступности размеров"
                    self.warning_msgs.append(msg)
        return stocks
