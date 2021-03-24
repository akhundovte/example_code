
import asyncio
import concurrent.futures

from apps.parser.cookie_driver import CookieDriver

from .services import shop_service


async def set_actual_cookies():
    shops_data = await shop_service.get_shops_with_need_cookies()
    await _run_set_cookies(shops_data)
    for shop_data in shops_data:
        await shop_service.update_parse_params(
            shop_data.id, shop_data.parse_params
            )


async def _run_set_cookies(shops_data):
    loop = asyncio.get_running_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        await loop.run_in_executor(pool, _set_cookies, shops_data)


def _set_cookies(shops_data):
    with CookieDriver() as driver:
        for shop_data in shops_data:
            parse_params = shop_data.parse_params
            cookies_name = parse_params.get('cookies_name')
            parse_params['cookies'] = driver.get_cookies(shop_data.url, cookies_name)
