
from core.exceptions import ObjectDoesNotExist

from ..datacls import User


class UserService:

    def __init__(self, user_repository):
        self._user_repository = user_repository

    async def get_or_create_user(self, user_id_orig, first_name):
        try:
            user_obj = await self._user_repository.get_user_by_orig_id(user_id_orig)
        except ObjectDoesNotExist:
            user_obj = User(user_id_orig=user_id_orig, first_name=first_name)
            await self._user_repository.create_user(user_obj)
        return user_obj


class AdminService:
    def __init__(self, admin_repository):
        self._admin_repository = admin_repository

    async def get_admins_id_orig(self):
        return await self._admin_repository.get_admins_id_orig()
