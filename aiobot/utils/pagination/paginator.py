import collections.abc

from math import ceil

from .settings import MAX_COUNT_IN_PAGE


class InvalidPage(Exception):
    pass


class PageNotAnInteger(InvalidPage):
    pass


class EmptyPage(InvalidPage):
    pass


class Paginator:

    def __init__(self, per_page=None):
        """
        query_count указывается если оригинальный запрос с соединениями,
        то для получения общего кол-ва можно использовать более простой запрос
        """
        if per_page is None:
            per_page = MAX_COUNT_IN_PAGE
        self.per_page = int(per_page)
        self._count = None
        self._number = None

    def validate_number(self, number):
        """Validate the given 1-based page number."""
        try:
            if isinstance(number, float) and not number.is_integer():
                raise ValueError
            number = int(number)
        except (TypeError, ValueError):
            raise PageNotAnInteger('That page number is not an integer')
        if number < 1:
            raise EmptyPage('That page number is less than 1')
        if number > self.num_pages:
            if number == 1:
                pass
            else:
                raise EmptyPage('That page contains no results')
        return number

    def get_page(self, records):
        return self._get_page(records, self._number, self)

    def set_count_and_page_number(self, count, number):
        self._count = count
        self._set_page_number(number)

    def _set_page_number(self, number):
        if self._number is None:
            self._number = self.validate_number(number)

    @property
    def offset(self):
        return (self._number - 1) * self.per_page

    def _get_page(self, *args, **kwargs):
        return Page(*args, **kwargs)

    @property
    def num_pages(self):
        """Return the total number of pages."""
        hits = max(1, self.count)
        return ceil(hits / self.per_page)

    @property
    def count(self):
        """Return the total number of objects, across all pages."""
        if self._count is None:
            raise ValueError('before need call set_count')
        return self._count


class Page(collections.abc.Sequence):

    def __init__(self, object_list, number, paginator):
        self.object_list = object_list
        self.number = number
        self.paginator = paginator

    def __len__(self):
        return len(self.object_list)

    def __getitem__(self, index):
        if not isinstance(index, (int, slice)):
            raise TypeError

        if not isinstance(self.object_list, list):
            self.object_list = list(self.object_list)
        return self.object_list[index]

    def has_next(self):
        return self.number < self.paginator.num_pages

    def has_previous(self):
        return self.number > 1

    def has_other_pages(self):
        return self.has_previous() or self.has_next()

    @property
    def all_count(self):
        return self.paginator.count

    @property
    def next_page_number(self):
        return self.number + 1

    @property
    def previous_page_number(self):
        return self.number - 1

    def start_index(self):
        if self.paginator.count == 0:
            return 0
        return (self.paginator.per_page * (self.number - 1)) + 1

    def end_index(self):
        if self.number == self.paginator.num_pages:
            return self.paginator.count
        return self.number * self.paginator.per_page
