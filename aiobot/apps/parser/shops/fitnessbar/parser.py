import json

from lxml import html
from decimal import Decimal
from urllib.parse import urlparse

from utils.client_async import AdapterAioHttp, ConnectionAioHttp

from ...exceptions import ParseError
from ...base_parser import BaseParser



class Parser(BaseParser):
    shop_name = 'fitnessbar'

    async def get_response_and_parse(self, url: str, **kwargs):
        """Вызывается в views.py
        """
        adapter = AdapterAioHttp()
        _connector = adapter.get_connector()
        async with _connector as connector:
            response_raw = await connector.perform_request(url=url)
            return await self.parse_response(response_raw,
                                             connector=connector,
                                             url_parse=url,
                                             )

    async def parse_response(
        self,
        response_raw: bytes,
        connector: ConnectionAioHttp,
        **kwargs
    ):
        """
        Вызывается в tasks.py и из self.get_response_and_parse()
        уникально тем, что есть второй запрос после обработки результатов первого
        """
        # возникала ошибка на byte 0xd0, отменил возбуждение UnicodeError
        url_parse = kwargs.get('url_parse')
        response_data = response_raw.decode(encoding='utf-8', errors='backslashreplace')
        try:
            product_data, product_stocks, type_list, product_main_name = self._parse(response_data, **kwargs)
            if len(type_list) > 1:
                products = []
                for type_data in type_list:
                    if type_data['code'] == product_data['reference']:
                        products.append(product_data)
                    else:
                        response_raw = await connector.perform_request(url=type_data['url'])
                        product_data_i, product_stocks_i = self._parse_second(
                            response_raw.decode(encoding='utf-8', errors='backslashreplace'),
                            product_main_name, type_data
                            )
                        products.append(product_data_i)
                        product_stocks.extend(product_stocks_i)

                products[0]['parameters'] = {'types': type_list}
                products[0]['stocks'] = product_stocks
                parse_result = {'data': products}
            else:
                product_data['stocks'] = product_stocks
                parse_result = {'data': product_data}

        except (LookupError, TypeError, ValueError, ParseError) as e:  # LookupError parent of IndexError, KeyError
            message_user = None
            if isinstance(e, ParseError):
                message_user = e.message_user
            raise ParseError(f"Парсер {self.shop_name} - ошибка {type(e)}: {str(e)}", message_user=message_user)

        await self.check_and_send_warnings(url_parse)
        return parse_result

    def _parse(self, content, **kwargs):
        url_parse = kwargs.get('url_parse')

        url_struct = urlparse(url_parse)
        host = '%s://%s' % (url_struct.scheme, url_struct.netloc)

        tree = html.fromstring(content)

        product_main_name = None
        product_type = None

        type_list_el = tree.cssselect("form.b-p-d-pack a.b-p-d-pack__item")
        # url_parse = host + type_list_el[0].attrib['href']
        type_list = []
        for type_item in type_list_el:
            url = host + type_item.attrib['href']
            code = type_item.attrib['data-product-id']
            name = type_item.attrib['data-product-package']
            type_data = {'code': code, 'name': name, 'url': url}
            if 'active' in type_item.attrib['class']:
                product_type = type_data
            type_list.append(type_data)

            if product_main_name is None:
                product_main_name = type_item.attrib['data-product-model']

        # так берем окончание пути в ссылке
        # url_parts = url.split('/')
        # reference = url_parts[-1]
        # if not reference:
        #     reference = url_parts[-2]

        product_data = self._get_product_data(product_main_name, product_type)
        product_stocks = self._get_stocks_from_parse_params(product_type['code'], tree)
        return product_data, product_stocks, type_list, product_main_name

    def _get_product_data(self, product_name, product_type):
        # if product_type['name']:
        #     product_name = f"{product_name} {product_type['name']}"
        return {
            'url': product_type['url'],
            'url_parse': product_type['url'],
            'name': product_name,
            'reference': product_type['code'],
            }

    def _parse_second(self, content, product_name, product_type):
        tree = html.fromstring(content)
        product_data = self._get_product_data(product_name, product_type)
        product_stocks = self._get_stocks_from_parse_params(product_type['code'], tree)
        return product_data, product_stocks

    def _get_stocks_from_parse_params(self, type_code, tree):
        """
        """
        params_list = tree.cssselect("div.b-p-t-inner--taste")
        stocks = []
        for param in params_list:
            price_base = None
            price_sale = None

            box_name_price = param.cssselect("div.b-p-t-inner__top")[0]
            name = box_name_price.cssselect("div.b-p-t-inner__name")[0].text.strip()

            if name.lower() == 'нет в наличии':
                msg = ("На данный момент для сайта fitnessbar "
                       "бот не поддерживает отслеживание товаров, которых нет в наличии")
                raise ParseError(msg, message_user=msg)

            data_param = param.xpath("div[@class='b-p-t-inner__end']/a")[0].attrib.get('data-product')
            if not data_param:
                continue
            sku = json.loads(data_param)['ID']

            price_box_el = box_name_price.xpath("div[@class='b-price']")
            if price_box_el:
                available = True
                price_box = price_box_el[0]
                price_new = price_box.xpath("div[@class='b-price__new']")
                price_old = price_box.xpath("div[@class='b-price__old']")
                price_normal = price_box.xpath("div[@class='b-price__normal']")

                if price_normal:
                    price_base = price_sale = price_normal[0].text
                elif price_new and price_old:
                    price_sale = price_new[0].text
                    price_base = price_old[0].text
                else:
                    self.warning_msgs.append("Цены заданы странно")
            else:
                available = False

            stocks.append({
                'sku': sku, 'available': available,
                'price_base': Decimal(''.join(price_base.split())),
                'price_sale': Decimal(''.join(price_sale.split())),
                'parameters': {
                    'type_code': type_code,
                    'option_code': name, 'option_name': name
                    },
                })
        return stocks
