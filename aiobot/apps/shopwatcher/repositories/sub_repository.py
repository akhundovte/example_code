import sqlalchemy as sa


from sqlalchemy import and_, String, func, cast  # false, cast
from sqlalchemy.dialects.postgresql import ARRAY


from apps.shopwatcher.tables import (
    sub_user, sub_user_stock_ix,
    product_stock, product, shop
    )
from utils.timezone import now
from db import db_engine
from db.aiopg import connection_ctx, begin_transaction  # , _TransactionContextManager

from core.exceptions import ObjectDoesNotExist, PermissionDenied

from .decorators import db_connect_classmethod
from ..datacls import Subscription


class SubSaveRepository:

    # def begin(self):
    #     return _TransactionContextManager(db_engine)

    def begin(self):
        return begin_transaction(db_engine)

    async def get_subscription_id(self, user_id, product_id):
        """
        используется SELECT FOR UPDATE
        """
        sub_user_query = sa.select((sub_user.c.id, ))\
            .where(and_(sub_user.c.product_id == product_id, sub_user.c.user_id == user_id))\
            .with_for_update()

        current_connection = connection_ctx.get()
        res = await current_connection.execute(sub_user_query)
        sub_id = await res.scalar()
        if not sub_id:
            raise ObjectDoesNotExist
        return sub_id

    async def get_stock_ids_set_by_product_id_and_codes(
        self, product_id, type_codes, option_codes
    ):
        stock_query = self._get_stock_query_by_product_id_and_codes(
            product_id, type_codes, option_codes
            )
        current_connection = connection_ctx.get()
        res = await current_connection.execute(stock_query)
        stock_records = await res.fetchall()
        return set((rec[0] for rec in stock_records))

    async def get_stock_ids_set_from_sub_stock(self, sub_id):
        query = sa.select((sub_user_stock_ix.c.stock_id, ))\
            .where(sub_user_stock_ix.c.sub_id == sub_id)
        current_connection = connection_ctx.get()
        res = await current_connection.execute(query)
        stock_records = await res.fetchall()
        return set((rec[0] for rec in stock_records))

    async def create_sub_user_and_stock_by_product_id(
        self, user_id, product_id, type_codes=None, option_codes=None
    ):
        current_connection = connection_ctx.get()
        parent_product_id = await self._get_product_parent_id_by_product_id(current_connection, product_id)
        if parent_product_id:
            product_id_for_sub = parent_product_id
        else:
            product_id_for_sub = product_id
        sub_id = await self._create_sub_user(current_connection, user_id, product_id_for_sub)
        await self._create_sub_user_stock_by_product_id(
            current_connection, product_id, type_codes, option_codes, sub_id)

    async def update_sub_user_stock(self, sub_id, delete_ids, add_ids):
        current_connection = connection_ctx.get()
        if delete_ids:
            await self._delete_sub_user_stock(current_connection, sub_id, delete_ids)
        if add_ids:
            await self._add_sub_user_stock(current_connection, sub_id, add_ids)
        await self._set_sub_user_dt_now(current_connection, sub_id)

    async def _create_sub_user(self, db_connection, user_id, product_id):
        query = sub_user.insert().values(
            product_id=product_id,
            user_id=user_id,
            dt_updated=now()
            )
        res_insert = await db_connection.execute(query)
        return await res_insert.scalar()

    async def _create_sub_user_stock_by_product_id(
        self, db_connection, product_id, type_codes, option_codes, sub_id
    ):
        stock_query = self._get_stock_query_by_product_id_and_codes(
            product_id, type_codes, option_codes, sub_id
            )
        query = sub_user_stock_ix.insert().from_select(('sub_id', 'stock_id'), stock_query)
        await db_connection.execute(query)

    async def _delete_sub_user_stock(self, db_connection, sub_id, delete_ids):
        query = sub_user_stock_ix.delete().where(and_(
            sub_user_stock_ix.c.stock_id.in_(delete_ids),
            sub_user_stock_ix.c.sub_id == sub_id,
            ))
        await db_connection.execute(query)

    async def _add_sub_user_stock(self, db_connection, sub_id, add_ids):
        insert_values = [
            {'stock_id': stock_id, 'sub_id': sub_id} for stock_id in add_ids
            ]
        query = sub_user_stock_ix.insert().values(insert_values)
        await db_connection.execute(query)

    async def _set_sub_user_dt_now(self, db_connection, sub_id):
        sub_update_q = sub_user.update().values(dt_updated=now())\
            .where(sub_user.c.id == sub_id)
        await db_connection.execute(sub_update_q)

    def _get_stock_query_by_product_id_and_codes(
        self, product_id, type_codes, option_codes, sub_id=None
    ):
        """
        """
        if sub_id is not None:
            stock_query = sa.select((sub_id, product_stock.c.id))
        else:
            stock_query = sa.select((product_stock.c.id, ))

        stock_query = stock_query.where(product_stock.c.product_id == product_id)

        if type_codes is not None:
            stock_query = stock_query.where(
                product_stock.c.parameters['type_code'].has_any(cast(type_codes, ARRAY(String())))
                )
        if option_codes is not None:
            stock_query = stock_query.where(
                product_stock.c.parameters['option_code'].has_any(cast(option_codes, ARRAY(String())))
                )
        return stock_query

    async def _get_product_parent_id_by_product_id(self, db_connection, product_id):
        query = sa.select((product.c.parent_id, ))\
            .where(product.c.id == product_id)
        res = await db_connection.execute(query)
        return await res.scalar()


class SubUserRepository:

    @db_connect_classmethod
    async def get_count_subs(self, db_connection, user_id):
        query_count = sa.select((func.count(), ))\
            .select_from(sub_user)\
            .where(sub_user.c.user_id == user_id)
        res = await db_connection.execute(query_count)
        return await res.scalar()

    @db_connect_classmethod
    async def get_sample_subs(self, db_connection, user_id, limit, offset):
        """
        SELECT pr.name, pr.url, pr.reference, pr.parameters,
        sh.name as shop_label,
        json_agg(prs.parameters) as selected_options
        FROM sub_user as sub
        INNER JOIN sub_user_stock_ix as subi ON subi.sub_id = sub.id
        INNER JOIN product_stock as prs ON prs.id = subi.stock_id
        INNER JOIN product as pr ON pr.id = prs.product_id
        INNER JOIN shop as sh ON sh.id = pr.shop_id
        WHERE user_id = 1
        GROUP BY sub.id, pr.id, sh.id
        ORDER BY sub.dt_created DESC
        """
        query = sa.select((sub_user.c.id, product.c.name, product.c.url, product.c.reference, product.c.parameters,
                           shop.c.label.label('shop_label'),
                           func.json_agg(product_stock.c.parameters).label('selected_options'))
                          )\
            .select_from(sub_user
                         .join(sub_user_stock_ix, sub_user_stock_ix.c.sub_id == sub_user.c.id)
                         .join(product_stock, product_stock.c.id == sub_user_stock_ix.c.stock_id)
                         .join(product, product.c.id == product_stock.c.product_id)
                         .join(shop, shop.c.id == product.c.shop_id)
                         )\
            .where(sub_user.c.user_id == user_id)\
            .group_by(sub_user.c.id, product.c.id, shop.c.id)\
            .order_by(sub_user.c.dt_created.desc())\
            .limit(limit).offset(offset)
        res = await db_connection.execute(query)
        records = await res.fetchall()
        return [Subscription.from_row(row) for row in records]

    @db_connect_classmethod
    async def get_sub_by_id(self, db_connection, sub_id, user_id):
        query = sa.select((sub_user.c.id, sub_user.c.user_id,
                           product.c.name, product.c.url, product.c.reference, product.c.parameters,
                           shop.c.label.label('shop_label'),
                           func.json_agg(product_stock.c.parameters).label('selected_options'))
                          )\
            .select_from(sub_user
                         .join(sub_user_stock_ix, sub_user_stock_ix.c.sub_id == sub_user.c.id)
                         .join(product_stock, product_stock.c.id == sub_user_stock_ix.c.stock_id)
                         .join(product, product.c.id == product_stock.c.product_id)
                         .join(shop, shop.c.id == product.c.shop_id)
                         )\
            .where(sub_user.c.id == sub_id)\
            .group_by(sub_user.c.id, product.c.id, shop.c.id)
        res = await db_connection.execute(query)
        row = await res.first()

        if not row:
            raise ObjectDoesNotExist
        if row.user_id != user_id:
            raise PermissionDenied

        return Subscription.from_row(row)

    @db_connect_classmethod
    async def delete_sub(self, db_connection, sub_id: int, user_id: int):
        query = sub_user.delete().where(and_(
            sub_user.c.id == sub_id,
            sub_user.c.user_id == user_id,
            ))
        await db_connection.execute(query)
