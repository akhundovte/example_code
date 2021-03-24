
from ...utils import get_jsondata_from_html
from ...base_parser import BaseParser


class Parser(BaseParser):
    shop_name = 'nike'
    key_json = 'INITIAL_REDUX_STATE'

    def _prepare_params(self, url: str, params):
        """ """
        _, color_selected = url.strip().rsplit('/', 1)
        params['color_selected'] = color_selected
        return url

    def _parse(self, content, **params):
        """
        """
        color_selected = params.get('color_selected')
        data = get_jsondata_from_html(content, self.key_json)
        product_url = data['App']['request']['URLS']['withoutStyleColor']

        sizes_stock_struct = {}
        types = []
        for color_code, color_data in data['Threads']['products'].items():
            color_name = f"{color_code} - {color_data['colorDescription']}"
            price_base = color_data['fullPrice']
            price_sale = color_data['currentPrice']

            sizes_shop = color_data['skus']
            for size in sizes_shop:
                if size['localizedSizePrefix']:
                    size_name = f"{size['localizedSizePrefix']} {size['localizedSize']}"
                else:
                    size_name = size['localizedSize']
                size_id = size['nikeSize']
                sizes_stock_struct[size['skuId']] = {
                    'sku': size['skuId'], 'available': False,
                    'price_base': price_base, 'price_sale': price_sale,
                    'parameters': {
                        'type_code': color_code,
                        'option_code': size_id, 'option_name': size_name,
                        }
                    }

            # в availableSkus содержатся только доступные для покупки размеры
            available_sizes_shop = color_data['availableSkus']
            for size in available_sizes_shop:
                sizes_stock_struct[size['skuId']]['available'] = size['available']

            types.append({
                'code': color_code,
                'name': color_name,
                'url': '%s/%s' % (product_url, color_code),
                })

        stocks = list(sizes_stock_struct.values())

        # предполагаем, что названия у всех цветов одинаковое
        color_first_code = types[0]['code']
        name = data['Threads']['products'][color_first_code]['title']
        # предполагаем, что в артикуле "Модель: CD6279-103" -> CD6279 уникально
        reference = color_first_code.partition('-')[0]

        product_data = {
            'name': name,
            'reference': reference,
            'url': product_url,
            'url_parse': product_url,
            'parameters': {
                'types': types
                },
            'stocks': stocks
            }

        return {
            'data': product_data,  # dict
            'selected': color_selected,  # str
            }
