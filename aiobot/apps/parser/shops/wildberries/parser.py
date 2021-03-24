import re
import json

from lxml import html

from ...exceptions import ParseError
from ...base_parser import BaseParser


class Parser(BaseParser):
    shop_name = 'wildberries'
    key_func = 'wb.spa.init'
    key_var = 'ssrModel'

    def _prepare_params(self, url: str, params):
        """
        """
        index = url.rfind('?')
        if index != -1:
            url_parse = url[:index]
        else:
            url_parse = url
        params['url_parse'] = url_parse
        return url_parse

    def _parse(self, content, **params):
        url_parse = params.get('url_parse')

        ref_pattern = re.compile(r'/\d+/')
        reference_with_bkt = ref_pattern.search(url_parse).group()
        reference_visit = reference_with_bkt[1:-1]

        url_tmplt = url_parse.replace(reference_with_bkt, "/%s/")

        data = self._get_jsondata_from_html(content)
        if not data:
            raise ParseError('не найден контейнер с данными в javascript')

        card_data = data['productCard']
        name = f"{card_data['goodsName']} ({card_data['brandName']})"

        products = []
        for reference, product_item in sorted(data['nomenclatures'].items(), key=lambda d: d[0]):
            stocks = []
            # basic_price = product_item['priceDetails']['basicPrice']
            name_type = product_item.get('rusName', '')
            if name_type:
                name_product = f"{name} {name_type}"
            else:
                name_product = name
            url_product = url_tmplt % reference
            if reference_visit == reference and url_product != url_parse:
                msg = f"разные ссылки {url_product} != {url_parse}"
                self.warning_msgs.append(msg)

            product_i = {
                'reference': reference,
                'url': url_product,
                'url_parse': url_product,
                'name': name_product,
                'stocks': stocks,
                }

            sizes = product_item['sizes']
            for sku, size_data in sizes.items():
                price_base = None
                price_sale = None
                size_available = size_data['addToBasketEnable']
                size_name = size_data['sizeName']
                size_name_rus = size_data.get('sizeNameRus')
                if size_name_rus:
                    size_label = f"{size_name} ({size_name_rus})"
                else:
                    size_label = size_name
                price_base_size = size_data['price']
                price_sale_size = size_data['priceWithSale']
                if price_base_size != 0:
                    price_base = price_base_size
                if price_sale_size != 0:
                    price_sale = price_sale_size

                stocks.append({
                    'sku': sku,
                    'price_base': price_base,
                    'price_sale': price_sale,
                    'available': size_available,
                    'parameters': {
                        "option_name": size_name,
                        "option_code": size_label
                        }
                    })
            products.append(product_i)

        return {
            'data': products,
            'selected': reference_visit,
            }

    def _get_jsondata_from_html(self, content):
        """
        поиск блока с данными неуниверсальный
        """
        offset = 29
        tree = html.fromstring(content)

        scripts_find = tree.xpath("//script[@type='text/javascript']/text()")
        for item in scripts_find:
            idx_func = item.find(self.key_func)
            if idx_func == -1:
                continue
            cut_script_text = item[idx_func+len(self.key_func):]

            idx_open_bkt = cut_script_text.find("({")
            idx_close_bkt = cut_script_text.find("});")
            if idx_open_bkt != -1 and idx_close_bkt != -1:
                cut_vars_text = cut_script_text[idx_open_bkt+1:idx_close_bkt+1]

                idx_var = cut_vars_text.find(self.key_var)
                if idx_var == -1:
                    continue

                cut_var_text = cut_vars_text[idx_var+len(self.key_var):]
                idx_open_bkt = cut_var_text.find("{")
                idx_close_bkt = cut_var_text.rfind("seoHelper")
                if idx_open_bkt != -1 and idx_close_bkt != -1:
                    return json.loads(cut_var_text[idx_open_bkt:idx_close_bkt-offset])
