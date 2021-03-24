import sqlalchemy as sa

from sqlalchemy import and_

from core.exceptions import ObjectDoesNotExist

from apps.shopwatcher.tables import shop

from ..datacls import Shop
from .decorators import db_connect_classmethod


class ShopRepository:

    @db_connect_classmethod
    async def get_shop_by_domain(
        self, db_connection, domain: str
    ) -> Shop:
        query = sa.select((shop.c.id, shop.c.name, shop.c.domain, shop.c.url, shop.c.label, shop.c.parse_params))\
            .where(and_(shop.c.domain == domain, shop.c.enabled == sa.true()))
        res = await db_connection.execute(query)
        row = await res.first()
        if not row:
            raise ObjectDoesNotExist('shop with domain %s does not exist' % domain)
        return Shop.from_row(row)

    @db_connect_classmethod
    async def get_supported_shops(self, db_connection) -> list:
        """
        список поддерживаемых магазинов
        """
        query = sa.select((shop.c.id, shop.c.name, shop.c.label, shop.c.domain, shop.c.url, shop.c.hostname))\
            .where(shop.c.enabled == sa.true()).order_by(shop.c.sort)
        shop_list = []
        async for row in db_connection.execute(query):
            shop_list.append(Shop.from_row(row))
        return shop_list

    @db_connect_classmethod
    async def get_shops_with_need_cookies(self, db_connection) -> list:
        """
        список магазинов, для которых надо собирать куки
        """
        query = sa.select((shop.c.id, shop.c.name, shop.c.domain, shop.c.url, shop.c.label, shop.c.parse_params))\
            .where(shop.c.need_cookies == sa.true())
        res = await db_connection.execute(query)
        records = await res.fetchall()
        return [Shop.from_row(row) for row in records]

    @db_connect_classmethod
    async def update_parse_params(self, db_connection, shop_id, shop_parse_params):
        query = shop.update().values(parse_params=shop_parse_params)\
            .where(shop.c.id == shop_id)
        await db_connection.execute(query)
