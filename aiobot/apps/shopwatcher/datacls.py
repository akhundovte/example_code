import attr

from typing import List

from decimal import Decimal


@attr.s(slots=True)
class User:
    first_name: str = attr.ib()
    user_id_orig: int = attr.ib()
    id: int = attr.ib(default=None)

    @classmethod
    def from_row(cls, row):
        return cls(**row)


@attr.s(slots=True, frozen=True)
class Shop:
    id: int = attr.ib()
    name: str = attr.ib()
    label: str = attr.ib()
    domain: str = attr.ib()
    url: str = attr.ib()
    hostname: dict = attr.ib(default=None)
    parse_params: dict = attr.ib(default=None)

    @classmethod
    def from_row(cls, row):
        return cls(**row)


@attr.s(slots=True)
class ProductStock:
    sku: str = attr.ib()
    available: bool = attr.ib()
    discount: int = attr.ib()
    price_base: Decimal = attr.ib()
    price_sale: Decimal = attr.ib()
    price_card: Decimal = attr.ib()
    # product_id: int = attr.ib()
    parameters: dict = attr.ib(default=None)
    id: int = attr.ib(default=None)


@attr.s(slots=True)
class Product:
    name: str = attr.ib()
    reference: str = attr.ib()
    url: str = attr.ib()
    url_parse: str = attr.ib(default=None)
    parameters: dict = attr.ib(default=None)
    stocks: List[ProductStock] = attr.ib(factory=list)
    shop_id: int = attr.ib(default=None)
    parent_id: int = attr.ib(default=None)
    id: int = attr.ib(default=None)

    @classmethod
    def from_bd_records(cls, product_record, stock_records):
        stocks = [ProductStock(**item) for item in stock_records]
        return cls(
            id=product_record.id,
            name=product_record.name, shop_id=product_record.shop_id,
            reference=product_record.reference, url=product_record.url,
            url_parse=product_record.url_parse, parameters=product_record.parameters,
            parent_id=product_record.parent_id, stocks=stocks
            )

    @classmethod
    def from_dict(cls, data):
        stocks = [ProductStock(**item) for item in data['stocks']]
        return cls(
            name=data['name'], shop_id=data['shop_id'],
            reference=data['reference'], url=data['url'],
            url_parse=data['url_parse'], parameters=data['parameters'],
            parent_id=data.get('parent_id'), stocks=stocks
            )

    def get_choices(self):
        """"""
        choices_type = []
        if (not self.parameters) or ('types' not in self.parameters):
            choices_option = get_choices_list_from_stocks(self.stocks)
            return [], choices_option
        else:
            if len(self.parameters['types']) == 0:
                raise ValueError("product_parameters['types'] must be filled")

            choices_option = get_choices_dict_from_stocks(self.stocks)
            choices_type = get_choices_list_from_types(self.parameters['types'])
            return choices_type, choices_option


def get_choices_list_from_types(types):
    choices_type = []
    for type_item in types:
        choices_type.append({
            'code': type_item['code'],
            'label': type_item['name']
            })
    return choices_type


def get_choices_list_from_stocks(stocks):
    choices_option = []
    for stock_item in stocks:
        if stock_item.parameters:
            choices_option.append({
                'code': stock_item.parameters['option_code'],
                'label': stock_item.parameters['option_name']
                })
    return choices_option


def get_choices_dict_from_stocks(stocks):
    choices_option = {}
    for stock_item in stocks:
        if stock_item.parameters:
            stock_parameters = stock_item.parameters
            if 'option_code' in stock_parameters:
                type_code = stock_parameters['type_code']
                choices_option_item = {
                    'code': stock_parameters['option_code'],
                    'label': stock_parameters['option_name']
                    }
                if type_code in choices_option:
                    choices_option[type_code].append(choices_option_item)
                else:
                    choices_option[type_code] = [choices_option_item, ]
    return choices_option


@attr.s(slots=True)
class Subscription:
    id: int = attr.ib()
    product_name: str = attr.ib()
    product_url: str = attr.ib()
    product_reference: str = attr.ib()
    shop_label: str = attr.ib()
    selected: list = attr.ib(default=None)

    @classmethod
    def from_row(cls, row):
        """
        Конструктор для формирования экземпляра на основе строки из БД
        """
        if row.parameters and 'types' in row.parameters:
            types_info = {item['code']: item for item in row.parameters['types']}
            selected = {}
            for item in row.selected_options:
                type_code = item.get('type_code')
                if type_code:
                    if 'option_code' in item:
                        if type_code in selected:
                            selected[type_code]['options'].append(item['option_name'])
                        else:
                            type_info = types_info[type_code]
                            selected[type_code] = {
                                'type_url': type_info['url'],
                                'type_name': type_info['name'],
                                'options': [item['option_name'], ]
                                }
                    else:
                        type_info = types_info[type_code]
                        selected[type_code] = {
                            'type_url': type_info['url'],
                            'type_name': type_info['name'],
                            }
            selected = list(selected.values())
        elif row.selected_options:
            # если нет ничего в stock parameters, то в списке будет пустое значение [null]
            # поэтому ставим условие
            options = [item['option_name'] for item in row.selected_options if item]
            selected = [{'options': options}, ]

        return cls(row.id, row.name, row.url, row.reference, row.shop_label, selected)
