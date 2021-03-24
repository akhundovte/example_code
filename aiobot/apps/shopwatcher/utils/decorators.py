import traceback

from functools import wraps, update_wrapper

from typing import (
    Optional, Union, Tuple  # , List
)

from aiogram import types

from settings.log import logger_service
from apps.shopwatcher.management import send_msg_admins


def log_except(func):
    @wraps(func)
    async def decorated(message_or_query: Union[types.Message, types.CallbackQuery], *args, **kwargs):
        try:
            return await func(message_or_query, *args, **kwargs)
        except Exception as e:
            tb = traceback.format_exc()
            msg_traceback = f"....\nOriginal exception was:\n {tb}"
            msg_log = (f"Ошибка в функции {func.__name__}:\nтип ошибки: {type(e)}\n"
                       f"текст ошибки: {str(e)} \n{msg_traceback}")
            await send_msg_admins(msg_log)
            logger_service.error(msg_log)

            msg_user = "Произошла ошибка, повторите действие или обратитесь к администратору."
            if isinstance(message_or_query, types.Message):
                await message_or_query.answer(msg_user)
            elif isinstance(message_or_query, types.CallbackQuery):
                await message_or_query.message.edit_text(msg_user)
    return decorated


def log_except_for_admin(func):
    @wraps(func)
    async def decorated(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            tb = traceback.format_exc()
            url = kwargs.get('url')
            msg_traceback = f"....\nOriginal exception was:\n {tb}"

            msg_log = (f"Ошибка в функции {func.__name__}:\nтип ошибки: {type(e)}\n"
                       f"текст ошибки: {str(e)} \n{msg_traceback}")
            if url:
                msg_log += f"\nПри обработке ссылки {url}"

            await send_msg_admins(msg_log)
            logger_service.error(msg_log)
    return decorated


def method_decorator(decorator):
    """
    Сделано в упрощенном варианте по method_decorator - django.utils.decorators.py
    """
    def _dec(method):
        def _wrapper(self, *args, **kwargs):
            bound_method = method.__get__(self, type(self))
            bound_method_dec = decorator(bound_method)
            return bound_method_dec(*args, **kwargs)
        update_wrapper(_wrapper, method)
        return _wrapper
    return _dec
