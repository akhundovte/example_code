
from marshmallow import (
    Schema, fields, validate,
    pre_load, post_load, ValidationError
    )


ERRORS_TEXT = {
    'max_str': 'Превышена возможная длина строки {max}'
    }


class ProductSchema(Schema):
    name = fields.String(
        required=True,
        validate=validate.Length(max=127, error=ERRORS_TEXT['max_str'])
        )
    url = fields.Url(
        allow_none=True, missing=None,
        schemes={'http', 'https'}, validate=validate.Length(max=1023)
        )
    url_parse = fields.Url(
        allow_none=True, missing=None,
        schemes={'http', 'https'}, validate=validate.Length(max=1023)
        )
    reference = fields.String(allow_none=True, missing=None, validate=validate.Length(max=127))
    dt_created = fields.DateTime(dump_only=True)
    parameters = fields.Dict(allow_none=True, missing=None)
    stocks = fields.List(fields.Nested('ProductStockSchema'), missing=lambda: [])

    @pre_load
    def process_data(self, data, **kwargs):
        reference = data.get('reference')
        if reference and isinstance(reference, int):
            try:
                reference = str(reference)
                data['reference'] = reference
            except (TypeError, ValueError):
                error_messages = {'reference': 'invalid convert integer'}
                raise ValidationError(error_messages)
        return data


class ProductStockSchema(Schema):
    """
    """
    sku = fields.String(required=True,
                        validate=validate.Length(max=63, error=ERRORS_TEXT['max_str']))
    price_base = fields.Decimal(allow_none=True, places=2, missing=None)
    price_sale = fields.Decimal(allow_none=True, places=2, missing=None)
    price_card = fields.Decimal(allow_none=True, places=2, missing=None)
    discount = fields.Integer(allow_none=True, missing=None)
    available = fields.Boolean(required=True)
    parameters = fields.Dict(missing=None, allow_none=True)

    @post_load
    def set_discount(self, data, **kwargs):
        price_base = data.get('price_base')
        price_sale = data.get('price_sale')
        if price_sale:
            discount = int(100 - (100 * price_sale/price_base))
            data['discount'] = discount
        return data


product_schema = ProductSchema()
product_stock_schema = ProductStockSchema()


field_template = "Ошибки в поле %s:\n"
nested_template = "номер элемента %s\n"


def errors_to_str(errors: dict):
    """
    Если есть поле типа nested, то ошибки в виде словаря,
    ключи - это номер позиционный списка вложенных схем
    """
    def list_to_str(values):
        txt = ''
        for value in values:
            txt += str(value) + '\n'
        return txt

    def nested_to_str(msg_error, value):
        """Используется рекурсия для любой глубины вложенности"""
        for idx, items in value.items():
            msg_error += nested_template % idx
            for field_i, value_i in items.items():
                msg_error += field_template % field_i
                if isinstance(value_i, list):
                    msg_error += list_to_str(value_i)
                elif isinstance(value_i, dict):
                    msg_error = nested_to_str(msg_error, value_i)
        return msg_error

    msg_error = ''
    for field, value in errors.items():
        msg_error += field_template % field
        if isinstance(value, list):
            msg_error += list_to_str(value)
        elif isinstance(value, dict):
            msg_error = nested_to_str(msg_error, value)
    return msg_error
