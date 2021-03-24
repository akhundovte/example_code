from aiogram import types

from typing import (
    Optional
)


class PollKeybord:
    """
    keyboard_data сохраняем в состоянии пользователя
    для выбора нескольких вариантов в одном опросе

    keyboard_data
        список - [{'label': ..., 'code': ..., 'selected': ...}, ]
        label только текст (без галочек)
    """
    # emoji - :heavy_check_mark: U+27014 (hex)
    check_mark = chr(10004)
    code_all = 'all'

    def __init__(
        self,
        data: Optional[list] = None,
    ) -> None:
        self._header: str = None
        self._markup = types.InlineKeyboardMarkup(row_width=1)
        self._data = data

    @property
    def header(self) -> str:
        if self._header is None:
            raise ValueError('property _header is empty')
        return self._header

    @property
    def markup(self) -> types.InlineKeyboardMarkup:
        return self._markup

    @property
    def data(self) -> list:
        """
        список - [{'label': ..., 'code': ..., 'selected': ...}, ]
        label только текст (без галочек)
        """
        if self._data is None:
            raise ValueError('property _data is empty')
        return self._data

    def get_selected_codes(self):
        if self._data is None:
            raise ValueError('property _data is empty')
        start_idx = 0
        selected_all = False
        first_choice = self._data[0]
        if self._code_is_all(first_choice['code']) and first_choice['selected']:
            selected_all = True
            start_idx = 1

        selected_types = []
        for item in self._data[start_idx:]:
            if selected_all or item['selected']:
                selected_types.append(item['code'])
        return selected_types

    def build_keyboard(
        self,
        choices: list,
        prefix: str,
        exists_next: bool,
        selected_code: Optional[str] = None,
        with_all: bool = False
    ) -> None:
        if with_all:
            choices = (
                {'label': 'Все варианты', 'code': f"{prefix}_{self.code_all}"},
                *choices
                )

        data = []
        label_selected = None
        for item in choices:
            label, code = item['label'], item['code']
            if selected_code is not None and selected_code == code:
                label_selected = label
                selected = True
            else:
                selected = False
            self._set_button(label, prefix, code, selected)

            data.append({'label': label, 'code': code, 'selected': selected})

        text_button_done = self._get_text_button_done(exists_next)
        self._set_button(text_button_done, prefix, 'done')
        self._header = self._get_header(text_button_done, label_selected)
        self._data = data

    def build_keyboard_after_select(
        self,
        selected_code: str,
        prefix: str,
        exists_next: bool
    ) -> None:
        start_idx = 0
        clear_other = False
        first_choice = self._data[0]
        if self._code_is_all(first_choice['code']):
            # очистить все галочки, если выбрали "Все варианты"
            if self._code_is_all(selected_code):
                if not first_choice['selected']:
                    clear_other = True
                selected = not first_choice['selected']
            else:
                selected = False

            first_choice['selected'] = selected
            self._set_button(
                first_choice['label'], prefix, first_choice['code'], selected
                )
            start_idx = 1

        for item in self._data[start_idx:]:
            code = item['code']
            prev_selected = item['selected']
            if selected_code == code:
                selected = not prev_selected
            elif clear_other:
                selected = False
            else:
                selected = prev_selected
            item['selected'] = selected
            self._set_button(item['label'], prefix, code, selected)

        text_button_done = self._get_text_button_done(exists_next)
        self._set_button(text_button_done, prefix, 'done')
        self._header = self._get_header(text_button_done)

    def _set_button(self, label, prefix, code, selected=False):
        if selected:
            label = f"{self.check_mark}{label}"
        row_btns = types.InlineKeyboardButton(label, callback_data=f"{prefix}_{code}")
        self._markup.row(row_btns)

    def _code_is_all(self, value):
        return value.endswith(self.code_all)

    def _get_text_button_done(self, exists_next):
        if exists_next:
            return 'Дальше'
        else:
            return 'Подписаться'

    def _get_header(
        self, text_button_done, note: Optional[str] = None
    ):
        header = f"Выберите один или несколько вариантов и нажмите {text_button_done}:"
        if note:
            header += f"\n(примечание: по ссылке выбран {note})"
        return header
