import sqlalchemy as sa

from sqlalchemy import and_


from apps.shopwatcher.tables import (
    product, price_history,
    product_stock, sub_user, shop, sub_user_stock_ix
    )
from utils.timezone import now
from core.exceptions import ObjectDoesNotExist, PermissionDenied
from db import db_engine as db


from .decorators import db_connect_classmethod
from ..datacls import Product


class ProductRepository:

    @db_connect_classmethod
    async def get_product_by_reference(self, db_connection, reference, shop_id):
        query = sa.select((
            product.c.id, product.c.name, product.c.url, product.c.url_parse,
            product.c.reference, product.c.shop_id, product.c.parent_id,
            product.c.parameters
            ))\
            .where(and_(
                product.c.reference == reference,
                product.c.shop_id == shop_id
                ))
        res = await db_connection.execute(query)
        # возвращает None, если нет записи
        product_record = await res.first()
        if not product_record:
            raise ObjectDoesNotExist

        query = sa.select((
            product_stock.c.id, product_stock.c.sku, product_stock.c.available,
            product_stock.c.parameters, product_stock.c.price_base, product_stock.c.price_sale,
            product_stock.c.price_card, product_stock.c.discount,
            ))\
            .where(product_stock.c.product_id == product_record.id)

        res = await db_connection.execute(query)
        stock_records = await res.fetchall()
        return Product.from_bd_records(product_record, stock_records)

    @db_connect_classmethod
    async def create_product_and_stocks(self, db_connection, product_obj):
        async with db_connection.begin():
            product_id = await self._create_product(db_connection, product_obj)
            if product_obj.stocks:
                await self._create_product_stocks(db_connection, product_id, product_obj.stocks)
            return product_id

    @db_connect_classmethod
    async def update_product_and_stocks(
        self,
        db_connection,
        product_id,
        update_product_data,
        stocks_create,
        stocks_update_data,
        stocks_delete_ids,
        set_available
    ) -> None:
        async with db_connection.begin():
            if update_product_data:
                await self._update_product(db_connection, product_id, update_product_data)
            if stocks_create:
                await self._create_product_stocks(db_connection, product_id, stocks_create)
            if stocks_update_data:
                await self._update_product_stock(db_connection, stocks_update_data)
            if stocks_delete_ids:
                await self._delete_product_stock(db_connection, stocks_delete_ids, set_available)

    @db_connect_classmethod
    async def create_price_history(self, db_connection, stock):
        query = price_history.insert().values(
            product_stock_id=stock.id,
            price_base=stock.price_base,
            price_sale=stock.price_sale,
            price_card=stock.price_card,
            dt=now()
            )
        await db_connection.execute(query)

    async def _create_product(self, db_connection, product_obj):
        product_create_q = product.insert().values(
            shop_id=product_obj.shop_id, parent_id=product_obj.parent_id,
            name=product_obj.name, url=product_obj.url,
            url_parse=product_obj.url_parse, reference=product_obj.reference,
            parameters=product_obj.parameters
            )
        res_insert = await db_connection.execute(product_create_q)
        return await res_insert.scalar()

    async def _create_product_stocks(self, db_connection, product_id: int, stocks: list):
        insert_values = [{
            'product_id': product_id, 'sku': item.sku,
            'available': item.available, 'discount': item.discount,
            'price_base': item.price_base, 'price_sale': item.price_sale,
            'price_card': item.price_card, 'parameters': item.parameters,
            } for item in stocks]
        query = product_stock.insert().values(insert_values)
        await db_connection.execute(query)

    async def _update_product(self, db_connection, product_id, update_data):
        query = product.update().values(**update_data)\
            .where(product.c.id == product_id)
        await db_connection.execute(query)

    async def _update_product_stock(self, db_connection, update_data):
        for stock_id, stock_data in update_data.items():
            query = product_stock.update().values(**stock_data)\
                .where(product_stock.c.id == stock_id)
            await db_connection.execute(query)

    async def _delete_product_stock(self, db_connection, stock_ids, set_available=False):
        if set_available:
            query = product_stock.delete().where(product_stock.c.id.in_(stock_ids))
        else:
            query = product_stock.update().values(available=False)\
                .where(product_stock.c.id.in_(stock_ids))
        await db_connection.execute(query)


class ProductSubRepository:

    @db_connect_classmethod
    async def get_product_for_sub(self, db_connection, sub_id, user_id):
        query = sa.select((
            product.c.id, product.c.name, product.c.shop_id, product.c.reference,
            product.c.url, product.c.url_parse, product.c.parameters, product.c.parent_id,
            sub_user.c.user_id
            ))\
            .select_from(sub_user.join(product, product.c.id == sub_user.c.product_id))\
            .where(sub_user.c.id == sub_id)

        res = await db_connection.execute(query)
        product_record = await res.first()

        if not product_record:
            raise ObjectDoesNotExist

        if product_record.user_id != user_id:
            raise PermissionDenied

        stock_records = await self._get_product_stock_rows(db_connection, product_record.id)
        product_obj = Product.from_bd_records(product_record, stock_records)
        return product_obj

    async def _get_product_stock_rows(self, db_connection, product_id):
        query = sa.select((
            product_stock.c.id, product_stock.c.sku, product_stock.c.available,
            product_stock.c.parameters, product_stock.c.price_base, product_stock.c.price_sale,
            product_stock.c.price_card, product_stock.c.discount,
            ))\
            .where(product_stock.c.product_id == product_id)

        res = await db_connection.execute(query)
        return await res.fetchall()

    @db_connect_classmethod
    async def get_product_parameters_and_stocks_for_sub(self, db_connection, sub_id, user_id):
        query = sa.select((product.c.id, product.c.parameters, sub_user.c.user_id))\
            .select_from(sub_user
                         .join(sub_user_stock_ix, sub_user_stock_ix.c.sub_id == sub_user.c.id)
                         .join(product_stock, product_stock.c.id == sub_user_stock_ix.c.stock_id)
                         .join(product, product.c.id == product_stock.c.product_id)
                         )\
            .where(sub_user.c.id == sub_id)\
            .group_by(product.c.id, sub_user.c.id)

        res = await db_connection.execute(query)
        row = await res.first()

        if not row:
            raise ObjectDoesNotExist
        if row.user_id != user_id:
            raise PermissionDenied

        product_id = row.id
        product_parameters = row.parameters

        query = sa.select((product_stock.c.parameters, ))\
            .where(product_stock.c.product_id == product_id)\
            .order_by(product_stock.c.id)

        res = await db_connection.execute(query)
        product_stocks = await res.fetchall()

        return product_id, product_parameters, product_stocks

    # нужно другой декоратор писать с проверкой AsyncGeneratorType
    # https://stackoverflow.com/questions/54712966/asynchronous-decorator-for-both-generators-and-coroutines
    # @db_connect_classmethod
    # async def get_product_for_sub_iter(self, db_connection):
    async def get_product_for_sub_iter(self):
        """
        Парсим только те товары, на которые есть подписка

        SELECT pr.id, pr.url_parse, pr.url, sh.name
        --pr.*, sh.name
        FROM product as pr
        INNER JOIN sub_user as ps ON ps.product_id = pr.id
        INNER JOIN shop as sh ON sh.id = pr.shop_id
        GROUP BY pr.id, sh.id
        ORDER BY pr.id;
        """
        async with db.engine.acquire() as db_connection:
            query = sa.select((
                product.c.url_parse, product.c.url, shop.c.parse_params,
                shop.c.id.label('shop_id'), shop.c.name.label('shop_name')
                ))\
                .select_from(
                    product
                    .join(sub_user, sub_user.c.product_id == product.c.id)
                    .join(shop, product.c.shop_id == shop.c.id)
                    )\
                .group_by(product.c.id, shop.c.id)\
                .order_by(product.c.id)

            async for row in db_connection.execute(query):
                yield row
