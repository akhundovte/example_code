from aiogram.dispatcher import filters

from apps.shopwatcher import views


def setup_routes(dp):
    handler = views.HandlerProductSubscription()

    dp.register_message_handler(
        handler.handle_url, regexp=r'(https?://[^\s]*)', state="*"
        )
    dp.register_callback_query_handler(
        handler.choice_type_step,
        state=views.Choice.wait_type_choice, regexp=r'first_(.*)'
        )
    dp.register_callback_query_handler(
        handler.choice_option_step,
        state=views.Choice.wait_option_choice, regexp=r'option_(.*)'
        )
    dp.register_callback_query_handler(
        handler.edit_subscription, regexp=r'edit_sub_([0-9]*)', state="*"
        )
    dp.register_callback_query_handler(
        handler.delete_subscription, regexp=r'delete_sub_([0-9]*)', state="*"
        )
    dp.register_message_handler(views.commands, commands=['start'], state="*")
    dp.register_message_handler(views.supported_shops, commands=['shops'], state="*")
    dp.register_message_handler(views.subscriptions_user, commands=['subs'], state="*")

    dp.register_message_handler(
        views.manage_subscription,
        filters.RegexpCommandsFilter(regexp_commands=[r'sub_([0-9]*)']), state="*"
        )
    dp.register_callback_query_handler(views.subscriptions_user, regexp=r'subs_page_([0-9]*)', state="*")
    dp.register_message_handler(views.handle_other, state="*")

