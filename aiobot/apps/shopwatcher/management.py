from apps.shopwatcher.bot import bot

from .services import admin_service


async def send_msg_admins(msg, is_html_mode=False):
    """Отправка сообщения администраторам"""
    if is_html_mode:
        parse_mode = 'HTML'
    else:
        parse_mode = None

    admins_ids = await admin_service.get_admins_id_orig()
    for admin_id in admins_ids:
        await bot.send_message(
            chat_id=admin_id, text=msg,
            parse_mode=parse_mode,
            disable_web_page_preview=True
            )


async def send_msg_user(user_id, msg):
    """Отправка сообщения пользователю"""
    await bot.send_message(
        chat_id=user_id, text=msg,
        parse_mode='HTML', disable_web_page_preview=True
        )
