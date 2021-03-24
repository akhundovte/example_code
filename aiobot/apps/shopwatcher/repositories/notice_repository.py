import sqlalchemy as sa

from sqlalchemy import func  # false, and_, tuple_,

from db import db_engine as db

from utils.timezone import now

from apps.shopwatcher.tables import (
    user, product, shop, product_stock,
    sub_user_stock_ix, sub_user, notice_stock, notice_msg, StatusNoticeEnum
    )

from .decorators import db_connect_classmethod


class NoticeRepository:

    @db_connect_classmethod
    async def get_notice_stocks(self, db_connection, stock_ids):
        query = notice_stock.select().where(notice_stock.c.stock_id.in_(stock_ids))
        result = await db_connection.execute(query)
        return await result.fetchall()

    @db_connect_classmethod
    async def save_notice_stocks(
        self,
        db_connection,
        create_notice_data=None,
        update_notice_data=None,
        delete_notice_ids=None,
    ):
        async with db_connection.begin():
            if create_notice_data:
                await self._create_notice_stocks(db_connection, create_notice_data)
            if update_notice_data:
                await self._update_notice_stocks(db_connection, update_notice_data)
            if delete_notice_ids:
                await self._delete_notice_stocks(db_connection, delete_notice_ids)

    async def _create_notice_stocks(self, db_connection, create_notice_data):
        insert_vals = [
            {'stock_id': stock_id, 'data': data}
            for stock_id, data in create_notice_data.items()
            ]
        insert_q = notice_stock.insert().values(insert_vals)
        await db_connection.execute(insert_q)

    async def _update_notice_stocks(self, db_connection, update_notice_stock_data):
        for stock_id, data in update_notice_stock_data.items():
            update_q = notice_stock.update().values(data=data)\
                .where(notice_stock.c.stock_id == stock_id)
            await db_connection.execute(update_q)

    async def _delete_notice_stocks(self, db_connection, notice_stock_ids):
        delete_q = notice_stock.delete().where(notice_stock.c.id.in_(notice_stock_ids))
        await db_connection.execute(delete_q)


class NoticeMessageRepository:

    async def create_notice_msgs(self, msgs):
        async with db.engine.acquire() as db_connection:
            query = notice_msg.insert().values(msgs)
            await db_connection.execute(query)

    async def notice_msg_for_send_iter(self):
        bulk_size = 10
        send_ids = []
        while True:
            dt_send = now()
            async with db.engine.acquire() as db_connection:
                # .where(notice_msg.c.dt_send.is_(None))\
                query = sa.select((notice_msg.c.id, user.c.user_id_orig, user.c.first_name, notice_msg.c.text))\
                    .select_from(notice_msg.join(user, user.c.id == notice_msg.c.user_id))\
                    .where(notice_msg.c.status == StatusNoticeEnum.not_send.value)\
                    .order_by(user.c.id)\
                    .limit(bulk_size)
                res = await db_connection.execute(query)
                recs = await res.fetchall()

            if len(recs) == 0:
                break

            send_ids.clear()
            for item in recs:
                yield item.user_id_orig, item.first_name, item.text
                send_ids.append(item.id)

            async with db.engine.acquire() as db_connection:
                query = notice_msg.update().values(
                    dt_send=dt_send, status=StatusNoticeEnum.in_progress.value
                    )\
                    .where(notice_msg.c.id.in_(send_ids))
                await db_connection.execute(query)

    async def get_notice_product_iter(self):
        """
        SELECT
        sub.user_id, p.id as product_id, p.name as product_name, p.url as product_url,
        s.label as shop_label, p.parameters as product_parameters,
        json_agg(json_build_object('data', ns.data, 'parameters', ps.parameters, 'discount', ps.discount))
        FROM sub_user_stock_ix as subi
        INNER JOIN notice_stock as ns ON ns.stock_id = subi.stock_id
        INNER JOIN sub_user as sub ON sub.id = subi.sub_id
        INNER JOIN product_stock as ps ON ps.id = subi.stock_id
        INNER JOIN product as p ON p.id = ps.product_id
        INNER JOIN shop as s ON s.id = p.shop_id
        GROUP BY sub.user_id, p.id, s.id
        ORDER BY sub.user_id, p.id
        """
        async with db.engine.acquire() as db_connection:
            select_exists = sa.select((sa.exists(sa.select((notice_stock.c.stock_id, ))),))
            res = await db_connection.execute(select_exists)
            exists = await res.scalar()
            if not exists:
                return

            query = sa.select((
                    sub_user.c.user_id,
                    product.c.id.label('product_id'), product.c.name.label('product_name'),
                    product.c.reference.label('product_reference'), product.c.url.label('product_url'),
                    product.c.parameters.label('product_parameters'),
                    func.json_agg(func.json_build_object(
                                    'data', notice_stock.c.data,
                                    'parameters', product_stock.c.parameters,
                                    'discount', product_stock.c.discount,
                                    )).label('notice_data'),
                    shop.c.label.label('shop_label')
                    ))\
                .select_from(
                    sub_user_stock_ix
                    .join(notice_stock, notice_stock.c.stock_id == sub_user_stock_ix.c.stock_id)
                    .join(sub_user, sub_user.c.id == sub_user_stock_ix.c.sub_id)
                    .join(product_stock, product_stock.c.id == sub_user_stock_ix.c.stock_id)
                    .join(product, product.c.id == product_stock.c.product_id)
                    .join(shop, shop.c.id == product.c.shop_id)
                    )\
                .group_by(sub_user.c.user_id, product.c.id, shop.c.id)\
                .order_by(sub_user.c.user_id, product.c.id)

            async for row in db_connection.execute(query):
                yield row

    async def delete_all_notice_stocks(self):
        delete_q = notice_stock.delete()
        async with db.engine.acquire() as db_connection:
            await db_connection.execute(delete_q)
