import sqlalchemy as sa

# from typing import (
#     List, Optional
# )

from apps.shopwatcher.tables import (
    user, user_group_ix, group, GroupEnum
    )
from core.exceptions import ObjectDoesNotExist

from ..datacls import User
from .decorators import db_connect_classmethod


class UserRepository:

    @db_connect_classmethod
    async def get_user_by_orig_id(
        self, db_connection, user_id_orig: int
    ) -> User:
        query = sa.select((user.c.id, user.c.user_id_orig, user.c.first_name))\
            .where(user.c.user_id_orig == user_id_orig)
        res = await db_connection.execute(query)
        row = await res.first()
        if not row:
            raise ObjectDoesNotExist(
                f'user with user_id_orig {user_id_orig} does not exist'
                )
        return User.from_row(row)

    @db_connect_classmethod
    async def create_user(
        self, db_connection, user_obj: User
    ) -> User:
        query = user.insert().values(
            user_id_orig=user_obj.user_id_orig,
            first_name=user_obj.first_name
            )
        res_insert = await db_connection.execute(query)
        user_obj.id = await res_insert.scalar()
        return user_obj


class AdminRepository:

    @db_connect_classmethod
    async def get_admins_id_orig(
        self, db_connection
    ):
        group_admin = GroupEnum.admin.value
        select_query = sa.select((user.c.user_id_orig, ))\
            .select_from(user
                         .join(user_group_ix, user_group_ix.c.user_id == user.c.id)
                         .join(group, group.c.id == user_group_ix.c.group_id)
                         ).where(group.c.name == group_admin)

        res = await db_connection.execute(select_query)
        rows = await res.fetchall()
        admins_ids = [item.user_id_orig for item in rows]
        return admins_ids
