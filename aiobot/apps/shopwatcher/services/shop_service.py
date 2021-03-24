# from core.exceptions import ObjectDoesNotExist

from ..datacls import Shop


class ShopService:

    def __init__(self, shop_repository):
        self.shop_repository = shop_repository

    async def get_shop_by_domain(self, domain: str) -> Shop:
        return await self.shop_repository.get_shop_by_domain(domain)

    async def get_supported_shops(self) -> list:
        return await self.shop_repository.get_supported_shops()

    async def get_shops_with_need_cookies(self) -> list:
        return await self.shop_repository.get_shops_with_need_cookies()

    async def update_parse_params(self, shop_id, shop_parse_params):
        await self.shop_repository.update_parse_params(shop_id, shop_parse_params)
