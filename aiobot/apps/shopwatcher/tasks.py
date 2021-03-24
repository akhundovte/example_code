import traceback

from utils.client_async import AdapterAioHttp

from settings.log import logger_service
from apps.shopwatcher.url_handler import ProductDataHandler
from apps.parser import get_parser, ParseError

from .management import send_msg_admins, send_msg_user
from .utils.decorators import log_except_for_admin
from .cookies import set_actual_cookies
from .services import product_sub_service, notice_msg_service


@log_except_for_admin
async def parse_products_task():
    """
    Парсинг товаров по ссылкам
    Необходима доработка: ссылки для парсинга складывать в Redis!!!
    """
    adapter = AdapterAioHttp(
        handler_response=handler_response,
        handler_errors=handler_errors
        )
    list_url = await product_sub_service.get_product_parse_data()
    result = await adapter.queue_request(list_url)
    if 'errors' in result:
        for error in result['errors']:
            msg_log = str(error)
            await send_msg_admins(msg_log)
            logger_service.error(msg_log)


async def handler_errors(error, **kwargs):
    msg_log = str(error)
    await send_msg_admins(msg_log)
    logger_service.error(msg_log)
    return True


@log_except_for_admin
async def handler_response(response, **kwargs):
    """
    Обработка результата запроса по ссылке
    """
    url_parse = kwargs['url']
    try:
        parser = get_parser(kwargs['shop_name'])
        parse_result = await parser.parse_response(
            response,
            url_parse=url_parse,
            url_product=kwargs.get('url_product'),
            connector=kwargs.get('connector'),
            headers=kwargs.get('headers'),
            cookies=kwargs.get('cookies')
            )
    except ParseError as e:
        tb = traceback.format_exc()
        msg_traceback = "....\nOriginal exception was:\n %s" % tb
        msg = f"Ошибка парсинга при обработке url {url_parse}, {str(e)}\n{msg_traceback}"
        await send_msg_admins(msg)
        return

    product_data = parse_result.get('data')
    await ProductDataHandler().handle(
        product_data, kwargs['shop_id'], kwargs.get('delete_not_exists_stock')
        )


@log_except_for_admin
async def send_notice_task():
    """Формирование и отправка оповещений пользователям."""
    await notice_msg_service.create_messages()
    await notice_msg_service.clear_notice_stocks()

    async for user_id, user_name, text in notice_msg_service.get_message_iter():
        await send_msg_user(user_id, text)
        msg_admin = f"Сообщение пользователю {user_name} ({user_id}):\n{text}"
        await send_msg_admins(msg_admin, is_html_mode=True)


async def everyday_msg_admins_task():
    msg_text = 'Ежедневная проверка работы бота'
    await send_msg_admins(msg_text)


async def set_actual_cookies_task():
    """Установка актуальных cookies
    только для магазинов, у которых need_cookies=True
    """
    await set_actual_cookies()
