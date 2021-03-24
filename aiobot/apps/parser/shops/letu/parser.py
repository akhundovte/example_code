import json

from urllib.parse import urlparse

from ...base_parser import BaseParser


class Parser(BaseParser):
    shop_name = 'letu'

    def _prepare_params(self, url: str, params):
        """ """
        url_struct = urlparse(url)
        url_path = url_struct.path
        key = '/sku/'
        idx_sku = url_path.find(key)
        # значит выбрана страничка с выбранным объемом
        sku_selected = None
        if idx_sku != -1:
            sku_selected = url_path[idx_sku + len(key):]
            url_path = url_path[:idx_sku]

        url_product = '%s://%s%s' % (url_struct.scheme, url_struct.netloc, url_path)
        url_parse = url_product + '?format=json'

        params['url_product'] = url_product
        params['sku_selected'] = sku_selected
        params['url_parse'] = url_parse
        return url_parse

    def _parse(self, data, **params):
        data = json.loads(data)
        url_product = params.get('url_product')
        url_parse = params.get('url_parse')
        sku_selected = params.get('sku_selected')

        products_content = data['contents'][0]['mainContent'][0]['contents'][0]['productContent']

        if (len(data['contents']) > 1 or len(data['contents'][0]['mainContent']) > 1 or
                len(data['contents'][0]['mainContent'][0]['contents']) > 1):
            msg = "по ключам contents, mainContent списки содержат более 1 элемента"
            self.warning_msgs.append(msg)

        # products_content - это список блоков с данными и текстом для страницы с карточкой товара
        # (и Описание и Информация о бренде) и обычно их 5
        # нужна сортировка т.к. меняется порядок из-за чего поле parameters в product перезаписывается
        product_list = sorted(products_content[0]['skuList'], key=lambda i: i['repositoryId'])
        code_selected = None
        stocks = []
        types = []
        for product in product_list:
            if not product['isAvailable']:
                msg = "product значение по ключу isAvailable = False"
                self.warning_msgs.append(msg)

            price_base = product['price']['rawTotalPrice']
            price_sale = product['price']['amount']
            price_card = product['priceWithMaxDCard']['amount']
            if price_sale == price_card:
                price_card = None

            sku = product['repositoryId']
            type_code = product['article']
            type_name = product['displayName']
            if sku_selected is not None and sku_selected == sku:
                code_selected = type_code

            stocks.append({
                'sku': sku, 'available': product['inStock'],
                'price_base': price_base, 'price_sale': price_sale, 'price_card': price_card,
                'parameters': {
                    'type_code': type_code,
                    }
                })
            types.append({
                'name': type_name,
                'code': type_code,
                'url': '%s/sku/%s' % (url_product, sku),
                })

        # data['canonical']
        product_main = products_content[0]['product']
        # product_main['sefPath']

        if not product_main['isAvailable']:
            # даже для товара НЕТ В НАЛИЧИИ было True, поэтому лучше отследить обратное поведение
            msg = "product_main значение по ключу isAvailable = False"
            self.warning_msgs.append(msg)

        product_data = {
            'name': product_main['displayName'],
            'url': url_product,
            'url_parse': url_parse,
            'reference': product_main['repositoryId'],
            'parameters': {
                'types': types
                },
            'stocks': stocks
            }

        return {
            'data': product_data,
            'selected': code_selected,
            }
