import attr
import traceback

from urllib.parse import urlparse

from core.exceptions import ObjectDoesNotExist

from apps.shopwatcher.serializers import errors_to_str
from apps.parser import get_parser, ParseError
from apps.shopwatcher.management import send_msg_admins

from .services import (
    product_service, shop_service,
    HandleMessageError, HandleProductError, DeserializeProductError
    )


@attr.s
class UrlHandlerUser:
    shop = attr.ib()
    product = attr.ib()
    selected_type = attr.ib()

    @classmethod
    async def handle(cls, url):
        url = url.strip()
        shop = await cls._get_shop_by_url(url)
        headers = None
        cookies = None
        if shop.parse_params:
            headers = shop.parse_params.get('headers')
            cookies = shop.parse_params.get('cookies')

        parse_result = await cls._parse_by_url(url, headers, cookies, shop.name)
        selected_type = parse_result.get('selected')

        delete_not_exists_stock = True
        if shop.parse_params:
            delete_not_exists_stock = shop.parse_params.get('delete_not_exists_stock')

        product = await ProductDataHandler().handle(
            parse_result['data'], shop.id, delete_not_exists_stock, selected_type
            )

        return cls(shop, product, selected_type)

    @classmethod
    async def _get_shop_by_url(cls, url):
        host = urlparse(url).netloc
        domain = '.'.join(host.split('.')[-2:])
        try:
            shop = await shop_service.get_shop_by_domain(domain)
        except ObjectDoesNotExist:
            message_error = "Нет поддержки данного магазина"
            raise HandleMessageError(message_error, message_user=message_error)
        return shop

    @classmethod
    async def _parse_by_url(cls, url, headers, cookies, shop_name):
        """Парсинг полученной ссылки
        выделяем домен первого и второго уровня - отбрасываем остальное
        чтобы не имело значение наличие www
        """
        try:
            parser = get_parser(shop_name)
            parse_result = await parser.get_response_and_parse(url, headers=headers, cookies=cookies)
        except ParseError as e:
            tb = traceback.format_exc()
            msg_traceback = "....\nOriginal exception was:\n %s" % tb
            raise HandleMessageError(
                f"Ошибка парсинга: {str(e)}\n{msg_traceback}",
                message_user=e.message_user
                )
        return parse_result


class ProductDataHandler:
    async def handle(
        self, product_data, shop_id, delete_not_exists_stock, selected_type=None
    ):
        handler = get_handler_data(product_data)
        try:
            result = await handler(
                product_data, shop_id,
                selected_type=selected_type,
                delete_not_exists_stock=delete_not_exists_stock
                )
        except HandleProductError as e:
            raise HandleMessageError(f"Ошибка обработки товара:\n{str(e)}")
        return result


def get_handler_data(product_data):
    if isinstance(product_data, dict):
        return _handle_product_data_as_dict
    elif isinstance(product_data, list):
        return _handle_product_data_as_list


async def _handle_product_data_as_dict(
    product_data, shop_id, **kwargs
):
    """
    Общий случай, когда в product_data содержатся данные для одной записи в таблицу product
    """
    delete_not_exists_stock = kwargs.get('delete_not_exists_stock')
    product = await _handle_product(
        product_data, shop_id, delete_not_exists_stock=delete_not_exists_stock
        )
    return product


async def _handle_product_data_as_list(
    product_data, shop_id, **kwargs
):
    selected_type = kwargs.get('selected_type')
    delete_not_exists_stock = kwargs.get('delete_not_exists_stock')

    if selected_type is not None:
        return await _handle_product_data_list_with_selected(
            product_data, shop_id, selected_type, delete_not_exists_stock
            )
    else:
        return await _handle_product_data_list_without_selected(
            product_data, shop_id, delete_not_exists_stock
            )


async def _handle_product_data_list_with_selected(
    product_data, shop_id, selected_type, delete_not_exists_stock
):
    product = None
    parent_product_data = product_data[0]
    parent_product = await _handle_product(
        parent_product_data, shop_id,
        delete_not_exists_stock=delete_not_exists_stock
        )

    if selected_type == parent_product.reference:
        product = parent_product

    for product_data_i in product_data[1:]:
        product_i = await _handle_product(
            product_data_i, shop_id, parent_product, delete_not_exists_stock)

        if selected_type == product_i.reference:
            product = product_i

    if not product:
        msg_error = f"не найден выбранный элемент: {selected_type}"
        raise HandleMessageError(msg_error)
    return product


async def _handle_product_data_list_without_selected(
    product_data, shop_id, delete_not_exists_stock
):
    parent_product_data = product_data[0]
    parent_product = await _handle_product(
        parent_product_data, shop_id,
        delete_not_exists_stock=delete_not_exists_stock
        )

    for product_data_i in product_data[1:]:
        await _handle_product(
            product_data_i, shop_id,
            parent_product=parent_product,
            delete_not_exists_stock=delete_not_exists_stock
            )
    return parent_product


async def _handle_product(
    product_data, shop_id, parent_product=None, delete_not_exists_stock=False
):
    try:
        product, msg_admins = await product_service.handle(
            product_data, shop_id=shop_id,
            parent_product=parent_product,
            delete_not_exists_stock=delete_not_exists_stock
            )
    except DeserializeProductError as e:
        if e.errors:
            msg_error = f"Ошибки валидации:\n{errors_to_str(e.errors)}"
            raise HandleMessageError(msg_error)
    if msg_admins:
        url = product_data.get('url')
        if url:
            msg_admins = f"Обработка товара {url}\n{msg_admins}"
        await send_msg_admins(msg_admins)
    return product
