from collections import Sequence
from sqlalchemy import tuple_

from ..http import urlsafe_base64_encode, urlsafe_base64_decode
from .settings import MAX_COUNT_IN_PAGE



class InvalidCursor(Exception):
    pass


class CursorPaginator(object):
    delimiter = '|'
    forward_direct_code = 'f'
    back_direct_code = 'b'

    def __init__(self, db_connection, query, ordering_fields, ordering_direction, per_page=None):
        self.db_connection = db_connection
        self.query = query
        self.ordering_fields = ordering_fields

        if ordering_direction == 'asc':
            is_ascending = True
        elif ordering_direction == 'desc':
            is_ascending = False
        else:
            ValueError("Invalid params 'ordering_direction', "
                       "value must be asc or desc")
        # по возрастанию ли
        self.is_ascending = is_ascending

        if per_page is None:
            per_page = MAX_COUNT_IN_PAGE
        self.per_page = per_page

    async def get_page(self, cursor=None):
        if cursor is not None:
            is_forward, query = self._apply_cursor(cursor)
        else:
            is_forward, query = True, self.query

        if self.is_ascending ^ is_forward:
            ordering_fields_dir = (item.desc() for item in self.ordering_fields)
        else:
            ordering_fields_dir = (item.asc() for item in self.ordering_fields)

        # специально берется на 1 элемент больше, чтобы определить есть ли следующая страница
        query = query.order_by(*ordering_fields_dir).limit(self.per_page+1)

        res = await self.db_connection.execute(query)
        records = await res.fetchall()
        items = records[:self.per_page]

        has_additional = len(records) > len(items)

        if not is_forward:
            items.reverse()

        if is_forward:
            has_next = has_additional
            has_previous = bool(cursor)
        else:
            has_next = bool(cursor)
            has_previous = has_additional

        return CursorPage(items, self, has_next, has_previous)

    def encode_forward_cursor(self, position):
        return self._encode_cursor(position, self.forward_direct_code)

    def encode_back_cursor(self, position):
        return self._encode_cursor(position, self.back_direct_code)

    def position_from_instance(self, instance):
        position = []
        for field in self.ordering_fields:
            attr = getattr(instance, field.name)
            position.append(str(attr))
        return position

    def _apply_cursor(self, cursor):
        is_forward, position = self._decode_cursor(cursor)
        if is_forward != self.is_ascending:
            query = self.query.where(tuple_(*self.ordering_fields) < position)
        else:
            query = self.query.where(tuple_(*self.ordering_fields) > position)
        return is_forward, query

    def _decode_cursor(self, cursor):
        """
        direction = (forward, back)
        """
        try:
            params = urlsafe_base64_decode(cursor).decode('utf8')
            direction, *position = params.split(self.delimiter)
            if direction == self.forward_direct_code:
                is_forward = True
            elif direction == self.back_direct_code:
                is_forward = False
            else:
                raise ValueError('Valuse direction params invalid')
            return is_forward, position
        except (TypeError, ValueError) as e:
            raise InvalidCursor(str(e))

    def _encode_cursor(self, position, direction):
        cursor = self.delimiter.join((direction, *position))
        encoded = urlsafe_base64_encode(cursor.encode('utf8'))
        return encoded


class CursorPage(Sequence):
    def __init__(self, items, paginator, has_next=False, has_previous=False):
        self.items = items
        self.paginator = paginator
        self._has_next = has_next
        self._has_previous = has_previous

    def __len__(self):
        return len(self.items)

    def __getitem__(self, index):
        return self.items.__getitem__(index)

    def has_next(self):
        return self._has_next

    def has_previous(self):
        return self._has_previous

    def has_other_pages(self):
        return self._has_next or self._has_previous

    @property
    def next_page(self):
        val_cursor = None
        if self._has_next:
            position = self.paginator.position_from_instance(self.items[-1])
            val_cursor = self.paginator.encode_forward_cursor(position)
        return val_cursor

    @property
    def previous_page(self):
        val_cursor = None
        if self._has_previous:
            position = self.paginator.position_from_instance(self.items[0])
            val_cursor = self.paginator.encode_back_cursor(position)
        return val_cursor
