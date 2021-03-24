import functools
import pytz

from datetime import datetime

from settings.settings import TIME_ZONE

# utc = pytz.utc
tz_msk = pytz.timezone('Europe/Moscow')
tz_utc = pytz.utc


'''
Взято из Django

TIME_ZONE = 'Europe/Moscow'

naive - Относительное время - нет информации о временной зоне (timezone)
aware - Абсолютное время - обладает временной зоной, которая вдобавок не пустая
'''


@functools.lru_cache()
def get_default_timezone():
    """
    Return the default time zone as a tzinfo instance.
    This is the time zone defined by settings.TIME_ZONE.
    """
    return pytz.timezone(TIME_ZONE)


# Utilities


def localtime(value=None, timezone=None):
    """
    Convert an aware datetime.datetime to local time.

    Only aware datetimes are allowed. When value is omitted, it defaults to
    now().

    Local time is defined by the current time zone, unless another time zone
    is specified.
    """
    if value is None:
        value = now()
    if timezone is None:
        timezone = get_default_timezone()
    # Emulate the behavior of astimezone() on Python < 3.6.
    if is_naive(value):
        raise ValueError("localtime() cannot be applied to a naive datetime")
    return value.astimezone(timezone)


def localdate(value=None, timezone=None):
    """
    Convert an aware datetime to local time and return the value's date.

    Only aware datetimes are allowed. When value is omitted, it defaults to
    now().

    Local time is defined by the current time zone, unless another time zone is
    specified.
    """
    return localtime(value, timezone).date()


def now():
    """
    Return an aware or naive datetime.datetime, depending on settings.USE_TZ.

    datetime.now() - относительное время без указания зоны (но зона учитывается)

    if settings.USE_TZ:
        # timeit показывает, что datetime.now(tz=utc) на 24 % медленнее
        return datetime.utcnow().replace(tzinfo=utc)
    else:
        return datetime.now()

    """
    # return aware - Абсолютное время
    # timeit показывает, что datetime.now(tz=utc) на 24 % медленнее
    return datetime.utcnow().replace(tzinfo=tz_utc)


# utcoffset() - Ничего не возвращается,
# если экземпляр datetime не имеет никакого установленного tzinfo
def is_aware(value):
    """
    Determine if a given datetime.datetime is aware.

    The concept is defined in Python's docs:
    http://docs.python.org/library/datetime.html#datetime.tzinfo

    Assuming value.tzinfo is either None or a proper datetime.tzinfo,
    value.utcoffset() implements the appropriate logic.
    """
    return value.utcoffset() is not None


def is_naive(value):
    """
    Determine if a given datetime.datetime is naive.

    The concept is defined in Python's docs:
    http://docs.python.org/library/datetime.html#datetime.tzinfo

    Assuming value.tzinfo is either None or a proper datetime.tzinfo,
    value.utcoffset() implements the appropriate logic.
    """
    return value.utcoffset() is None
