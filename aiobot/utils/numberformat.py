import re

from decimal import Decimal, InvalidOperation

DECIMAL_SEPARATOR = '.'
NUMBER_GROUPING = 3
THOUSAND_SEPARATOR = ' '


def numcomma(value, use_l10n=True):
    """
    Преобразует в строку с разделителем через каждые три цифры
    И убирает дробную часть если она не существует, например, 103.00
    Сделано с расчетом на преобразование из Decimal (числа из БД)

    за основу взяты:
        floatformat - django.template.defaultfilters.py
        intcomma - django.contrib.humanize.templatetags.humanize.py

    """
    if use_l10n:
        try:
            if not isinstance(value, Decimal):
                value = Decimal(value)
        # сюда попадаем, если строка имеет запятую, т.е. в виде float
        except (TypeError, ValueError, InvalidOperation):
            return numcomma(value, False)
        else:
            try:
                # таким образом определяем является ли дробная часть нулевой, так сделано в floatformat
                m = int(value) - value
            except (ValueError, OverflowError, InvalidOperation):
                return repr(value)

            if not m:
                # с таким параметром дробная часть откидывается
                decimal_pos = 0
            else:
                decimal_pos = None

            # mark_safe маркирует строку как ненуждающуюся в экранировании
            return format(
                value,
                decimal_sep=DECIMAL_SEPARATOR,
                decimal_pos=decimal_pos,
                grouping=NUMBER_GROUPING,
                thousand_sep=THOUSAND_SEPARATOR,
                force_grouping=True
                )

    # сюда попадаем, если строка имеет запятую, т.е. в виде float
    orig = str(value)
    new = re.sub(r"^(-?\d+)(\d{})", r'\g<1>' + THOUSAND_SEPARATOR + r'\g<2>', orig)
    # можно и так более универсально
    # new = re.sub(r"^(-?\d+)(\d{" +str(NUMBER_GROUPING)+ r"})", r'\g<1>' +THOUSAND_SEPARATOR+ r'\g<2>', orig)
    if orig == new:
        return new
    else:
        return numcomma(new, use_l10n)


def format(number, decimal_sep, decimal_pos=None, grouping=0, thousand_sep='',
           force_grouping=False, use_l10n=True):
    """
    Get a number (as a number or string), and return it as a string,
    using formats defined as arguments:

    * decimal_sep: Decimal separator symbol (for example ".")
    * decimal_pos: Number of decimal positions
    * grouping: Number of digits in every group limited by thousand separator.
        For non-uniform digit grouping, it can be a sequence with the number
        of digit group sizes following the format used by the Python locale
        module in locale.localeconv() LC_NUMERIC grouping (e.g. (3, 2, 0)).
    * thousand_sep: Thousand separator symbol (for example ",")
    """
    use_grouping = use_l10n
    use_grouping = use_grouping or force_grouping
    use_grouping = use_grouping and grouping != 0
    # Make the common case fast
    if isinstance(number, int) and not use_grouping and not decimal_pos:
        return number
    # sign
    sign = ''
    if isinstance(number, Decimal):
        # Format values with more than 200 digits (an arbitrary cutoff) using
        # scientific notation to avoid high memory usage in {:f}'.format().
        _, digits, exponent = number.as_tuple()
        if abs(exponent) + len(digits) > 200:
            number = '{:e}'.format(number)
            coefficient, exponent = number.split('e')
            # Format the coefficient.
            coefficient = format(
                coefficient, decimal_sep, decimal_pos, grouping,
                thousand_sep, force_grouping, use_l10n,
            )
            return '{}e{}'.format(coefficient, exponent)
        else:
            str_number = '{:f}'.format(number)
    else:
        str_number = str(number)
    if str_number[0] == '-':
        sign = '-'
        str_number = str_number[1:]
    # decimal part
    if '.' in str_number:
        int_part, dec_part = str_number.split('.')
        if decimal_pos is not None:
            dec_part = dec_part[:decimal_pos]
    else:
        int_part, dec_part = str_number, ''
    if decimal_pos is not None:
        dec_part = dec_part + ('0' * (decimal_pos - len(dec_part)))
    dec_part = dec_part and decimal_sep + dec_part
    # grouping
    if use_grouping:
        try:
            # if grouping is a sequence
            intervals = list(grouping)
        except TypeError:
            # grouping is a single value
            intervals = [grouping, 0]
        active_interval = intervals.pop(0)
        int_part_gd = ''
        cnt = 0
        for digit in int_part[::-1]:
            if cnt and cnt == active_interval:
                if intervals:
                    active_interval = intervals.pop(0) or active_interval
                int_part_gd += thousand_sep[::-1]
                cnt = 0
            int_part_gd += digit
            cnt += 1
        int_part = int_part_gd[::-1]
    return sign + int_part + dec_part
