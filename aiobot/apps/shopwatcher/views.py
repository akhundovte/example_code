import re

from typing import (
    Optional, Union, Tuple  # , List
)

from aiogram import types

from core.exceptions import ObjectDoesNotExist  # , DBError

from .services import (
    HandleMessageError,
    sub_save_service, sub_user_service,
    user_service, shop_service, product_sub_service
    )
from apps.shopwatcher.url_handler import UrlHandlerUser

from .bot import dp

from apps.shopwatcher.management import send_msg_admins

from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext

from utils.jinja2 import jinja_render

from .utils.decorators import log_except, method_decorator
from .keyboard import PollKeybord


class Choice(StatesGroup):
    wait_type_choice = State()
    wait_option_choice = State()


TEXTS_MSG = {
    'warning_msg': "Произошла ошибка, обратитесь к администратору",
    'sub_done': "Вы успешно подписались!",
    }


class HandlerProductSubscription:

    @method_decorator(log_except)
    async def handle_url(
        self, message: types.Message, state: FSMContext, regexp: re.Match
    ):
        """
        Обработчик запроса на подписку
        """
        user = await user_service.get_or_create_user(
            message.from_user.id, message.from_user.first_name
            )
        url = regexp.group(1)
        try:
            handler = await UrlHandlerUser.handle(url)
        except HandleMessageError as e:
            if e.message_user:
                await message.reply(e.message_user)
            else:
                await message.reply(TEXTS_MSG['warning_msg'])
            message_admin = f"При обработке '{url}' ошибка:\n{str(e)}"
            await send_msg_admins(message_admin)
            return

        product = handler.product
        choices_type, choices_option = product.get_choices()

        await self.send_preview_product(message, handler.shop, product)
        state_data = {
            'user_id': user.id,
            'product_id': product.id,
            }
        text, reply_markup = await self.prepare_choice(
            state, state_data, choices_type, choices_option, handler.selected_type
            )

        await message.answer(text, reply_markup=reply_markup)

    async def send_preview_product(self, message, shop, product):
        msg = jinja_render.render_template(
            'preview_product_msg.html', {'shop': shop, 'product': product}
            )
        await message.reply(msg, parse_mode='HTML')

    async def send_preview_products_group(self, message, shop, products):
        msg = jinja_render.render_template(
            'preview_products_msg.html', {'shop': shop, 'products': products}
            )
        await message.reply(msg, parse_mode='HTML')

    @method_decorator(log_except)
    async def edit_subscription(
        self,
        query: types.CallbackQuery,
        regexp: re.Match
    ):
        """Изменение подписки."""
        user = await user_service.get_or_create_user(
            query.from_user.id, query.from_user.first_name
            )
        sub_id = int(regexp.group(1))
        state = dp.current_state()
        state_fsm = await state.get_state()

        if state_fsm is not None:
            await state.reset_state()

        try:
            product = await product_sub_service\
                .get_product_for_edit_sub(sub_id, user.id)
        except ObjectDoesNotExist:
            raise HandleMessageError('Error ObjectDoesNotExist')

        choices_type, choices_option = product.get_choices()
        state_data = {
            'user_id': user.id,
            'product_id': product.id,
            }
        text, reply_markup = await self.prepare_choice(
            state, state_data, choices_type, choices_option
            )
        await query.message.edit_text(text, reply_markup=reply_markup)

    @method_decorator(log_except)
    async def delete_subscription(self, query: types.CallbackQuery,
                                  regexp: re.Match):
        """Удаление подписки."""
        user = await user_service.get_or_create_user(
            query.from_user.id, query.from_user.first_name
            )
        sub_id = int(regexp.group(1))
        await sub_user_service.delete_sub(sub_id, user.id)
        text = "Подписка удалена"
        await query.message.edit_text(text)

    async def prepare_choice(
        self, state, state_data, choices_type, choices_option,
        selected_type=None
    ) -> Tuple[str, Optional[types.InlineKeyboardMarkup]]:
        """
        Подготовка к опросу пользователя
        """
        if not choices_type:
            if not choices_option or len(choices_option) == 1:
                await self.subscribe(state, state_data)
                return TEXTS_MSG['sub_done'], None
            else:
                # в этом случае choices_option должна быть списком
                if not isinstance(choices_option, list):
                    raise ValueError('choices_option must be list')
                return await self.go_to_choice_options(state, choices_option, state_data)

        if len(choices_type) == 1:
            if not choices_option:
                await self.subscribe(state, state_data)
                return TEXTS_MSG['sub_done'], None
            else:
                selected_type = choices_type[0]['code']
                choices_option_sel = choices_option[selected_type]
                if len(choices_option_sel) == 1:
                    await self.subscribe(state, state_data)
                    return TEXTS_MSG['sub_done'], None
                # если кол-во типов = 1, то переход ко второму опросу - выбор параметров (размера)
                state_data['selected_types'] = [selected_type, ]
                return await self.go_to_choice_options(
                    state, choices_option_sel, state_data
                    )
        else:
            # переход к первому опросу (выбор типа продукта)
            exists_next = bool(choices_option)
            state_data['choices_option'] = choices_option

            return await self.go_to_choice_type(
                state, exists_next, choices_type, selected_type, state_data
                )

    @method_decorator(log_except)
    async def choice_type_step(
        self,
        query: types.CallbackQuery,
        state: FSMContext,
        regexp: Optional[re.Match] = None
    ) -> None:
        """
        Обработчик состояния выбора типов товара
        """
        def get_merged_options(choices_option, selected_types):
            options_merge = []
            exists_set = set()
            for selected_item in selected_types:
                for idx, item in enumerate(choices_option[selected_item]):
                    code = item['code']
                    if code not in exists_set:
                        options_merge.append(
                            {'code': code, 'label': item['label'], 'pos': idx}
                            )
                        exists_set.add(code)
            return sorted(options_merge, key=lambda item: item['pos'])

        selected_code = regexp.group(1)
        user_data = await state.get_data()
        keyboard_data = user_data['keyboard_data']
        choices_option = user_data['choices_option']

        if selected_code == 'done':
            selected_types = PollKeybord(data=keyboard_data).get_selected_codes()
            # пропускаем действие, если пользователь ничего не выбрал
            if not selected_types:
                return

            if not choices_option:
                # подписываемся
                await self.subscribe(state, user_data, selected_types=selected_types)
                await query.message.edit_text(TEXTS_MSG['sub_done'])
                return

            # переход ко второму опросу - выбор параметров (размера)
            if len(selected_types) > 1:
                choices_option_sel = get_merged_options(choices_option, selected_types)
            else:
                choices_option_sel = choices_option[selected_types[0]]

            if len(choices_option_sel) == 1:
                # подписываемся
                await self.subscribe(
                    state, user_data,
                    selected_types=selected_types,
                    selected_options=[choices_option_sel[0]['code'], ]
                    )
                await query.message.edit_text(TEXTS_MSG['sub_done'])
                return
            else:
                state_data = {'selected_types': selected_types}
                text, reply_markup = await self.go_to_choice_options(
                    state, choices_option_sel, state_data
                    )
                await query.message.edit_text(text, reply_markup=reply_markup)
                return
        else:
            # выбор типа товара повторно
            text, reply_markup = await self.set_selected_and_repeat_choice(
                state, selected_code, keyboard_data, 'first', bool(choices_option)
                )
            await query.message.edit_text(text, reply_markup=reply_markup)
        return

    @method_decorator(log_except)
    async def choice_option_step(
        self,
        query: types.CallbackQuery,
        state: FSMContext,
        regexp: Optional[re.Match] = None
    ) -> None:
        """
        Обработчик состояния выбора параметров
        """
        selected_code = regexp.group(1)
        # selected_code = query.data
        user_data = await state.get_data()

        if selected_code == 'done':
            selected_params = PollKeybord(data=user_data['keyboard_data']).get_selected_codes()
            if not selected_params:  # если ничего не выбрано, пропускаем
                return
            # подписываемся
            await self.subscribe(state, user_data, selected_options=selected_params)
            await query.message.edit_text(TEXTS_MSG['sub_done'])
        else:
            # выбор параметров для выбранного типа товара повторно
            text, reply_markup = await self.set_selected_and_repeat_choice(
                state, selected_code, user_data['keyboard_data'], 'option'
                )
            await query.message.edit_text(text, reply_markup=reply_markup)
        return

    async def go_to_choice_type(
        self, state, exists_next, choices_type, selected_type, state_data
    ) -> Tuple[str, types.InlineKeyboardMarkup]:
        """Переход к выбору типу товара или товара из группы по артикулу
        """
        keyboard = PollKeybord()
        keyboard.build_keyboard(
            choices=choices_type, selected_code=selected_type,
            exists_next=exists_next, prefix='first', with_all=True
            )
        state_data['keyboard_data'] = keyboard.data
        await state.update_data(data=state_data)
        await Choice.wait_type_choice.set()
        return keyboard.header, keyboard.markup

    async def go_to_choice_options(
        self, state, choices_option_l, state_data
    ) -> Tuple[str, types.InlineKeyboardMarkup]:
        """Переход к выбору параметров товара (для выбранного типа)
        """
        keyboard = PollKeybord()
        keyboard.build_keyboard(
            choices=choices_option_l, exists_next=False,
            prefix='option'
            )
        state_data['keyboard_data'] = keyboard.data
        await state.update_data(data=state_data)
        await Choice.wait_option_choice.set()
        return keyboard.header, keyboard.markup

    async def set_selected_and_repeat_choice(
        self, state, selected_code, keyboard_data, prefix, exists_next=False
    ) -> Tuple[str, types.InlineKeyboardMarkup]:
        """Повторный выбор - чтобы выбрать несколько вариантов
        """
        keyboard = PollKeybord(data=keyboard_data)
        keyboard.build_keyboard_after_select(
            selected_code=selected_code, prefix=prefix, exists_next=exists_next
            )
        await state.update_data(keyboard_data=keyboard.data)
        return keyboard.header, keyboard.markup

    async def subscribe(self, state, user_data, selected_types=None, selected_options=None) -> str:
        """Подписка с учетом выбранных параметров"""
        if selected_types is None:
            selected_types = user_data.get('selected_types')

        await sub_save_service.save(
            user_id=user_data['user_id'],
            product_id=user_data['product_id'],
            selected_types=selected_types,
            selected_options=selected_options
            )
        await state.finish()


@log_except
async def commands(message: types.Message):
    """Список доступных команд."""
    msg = jinja_render.render_template('commands_msg.html', {})
    await message.answer(msg)


@log_except
async def supported_shops(message: types.Message):
    """Список поддерживаемых магазинов."""
    shops = await shop_service.get_supported_shops()
    msg = jinja_render.render_template('shops_msg.html', {'shops': shops})
    await message.answer(msg, parse_mode='HTML', disable_web_page_preview=True)


@log_except
async def subscriptions_user(
    message: Union[types.Message, types.CallbackQuery],
    regexp: Optional[re.Match] = None
):
    """Список подписок пользователя."""
    if regexp is not None:
        page_number = regexp.group(1)
    else:
        page_number = 1

    user = await user_service.get_or_create_user(
        message.from_user.id, message.from_user.first_name
        )
    page = await sub_user_service.get_page_for_user(page_number, user.id)
    msg = jinja_render.render_template('sub_list_msg.html', {'page': page})

    keyboard = None
    buttons = []
    if page.has_previous():
        buttons.append(types.InlineKeyboardButton('Назад', callback_data=f"subs_page_{page.previous_page_number}"))
    if page.has_next():
        buttons.append(types.InlineKeyboardButton('Вперед', callback_data=f"subs_page_{page.next_page_number}"))
    if buttons:
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        keyboard.row(*buttons)

    if isinstance(message, types.Message):
        await message.answer(msg, reply_markup=keyboard, parse_mode='HTML', disable_web_page_preview=True)
    elif isinstance(message, types.CallbackQuery):
        await message.message.edit_text(msg, reply_markup=keyboard, parse_mode='HTML', disable_web_page_preview=True)


@log_except
async def manage_subscription(message: types.Message, regexp_command):
    """Изменение или удаление подписки."""
    sub_id = int(regexp_command.group(1))
    user = await user_service.get_or_create_user(
        message.from_user.id, message.from_user.first_name
        )
    sub_obj = await sub_user_service.get_sub(sub_id, user.id)
    msg = jinja_render.render_template('sub_msg.html', {'sub': sub_obj})

    keyboard = types.InlineKeyboardMarkup(row_width=2)
    but_edit = types.InlineKeyboardButton('Изменить', callback_data=f"edit_sub_{sub_id}")
    but_delete = types.InlineKeyboardButton('Удалить', callback_data=f"delete_sub_{sub_id}")
    keyboard.row(but_edit, but_delete)
    await message.answer(msg, reply_markup=keyboard, parse_mode='HTML', disable_web_page_preview=True)


@log_except
async def handle_other(message: types.Message):
    msg = 'Ваше сообщение не является ссылкой\nДля создания новой подписки отправьте, пожалуйста, ссылку на товар'
    await message.answer(msg, parse_mode='HTML', disable_web_page_preview=True)
