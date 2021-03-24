
from typing import (
    List, Optional
    )

from core.exceptions import ObjectDoesNotExist

from utils.pagination import Paginator


class SubSaveService:
    def __init__(self, sub_save_repository):
        self._sub_save_repository = sub_save_repository

    async def save(
        self,
        user_id: int,
        product_id: Optional[int] = None,
        selected_types: Optional[List[str]] = None,
        selected_options: Optional[List[str]] = None,
    ):
        """
        Использование контекстного менеджера обязательно для создания транзакции
        в запросе get_subscription_id используется блокировка записи при помощи SELECT FOR UPDATE
        """
        async with self._sub_save_repository.begin():
            try:
                sub_id = await self._sub_save_repository.get_subscription_id(user_id, product_id)
                ids_set_last = await self._sub_save_repository.get_stock_ids_set_from_sub_stock(sub_id)
                ids_set_new = await self._sub_save_repository.get_stock_ids_set_by_product_id_and_codes(
                    product_id, selected_types, selected_options
                    )
                delete_ids = ids_set_last - ids_set_new
                add_ids = ids_set_new - ids_set_last
                await self._sub_save_repository.update_sub_user_stock(sub_id, delete_ids, add_ids)

            except ObjectDoesNotExist:
                await self._sub_save_repository.create_sub_user_and_stock_by_product_id(
                    user_id, product_id, selected_types, selected_options
                    )


class SubUserService:

    def __init__(self, sub_user_repository):
        self._sub_user_repository = sub_user_repository

    async def get_page_for_user(self, page_number, user_id):
        paginator = Paginator(per_page=5)
        count = await self._sub_user_repository.get_count_subs(user_id)
        paginator.set_count_and_page_number(count, page_number)

        subs = await self._sub_user_repository.get_sample_subs(
            user_id, limit=paginator.per_page, offset=paginator.offset
            )
        page = paginator.get_page(subs)
        return page

    async def delete_sub(
        self, sub_id: int, user_id: int
    ):
        await self._sub_user_repository.delete_sub(sub_id, user_id)

    async def get_sub(
        self, sub_id: int, user_id: int
    ):
        return await self._sub_user_repository.get_sub_by_id(sub_id, user_id)
