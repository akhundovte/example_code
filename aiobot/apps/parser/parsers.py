from importlib import import_module

from .exceptions import ParserImportError


template_location = 'apps.parser.shops.%s.parser'

_parser_cache = {}


def get_parser(shop_name):
    try:
        return _parser_cache[shop_name]()
    except KeyError:
        pass
    try:
        module = import_module(template_location % shop_name)
    except ImportError as e:
        raise ParserImportError(f"Ошибка {type(e)}: {str(e)}")
    class_val = getattr(module, 'Parser', None)
    if class_val is None:
        raise ParserImportError(f"module {module.__name__} has not class Parser")
    _parser_cache[shop_name] = class_val
    return class_val()


def reset_parser_cache():
    """Clear cached parsers.
    """
    global _parser_cache
    _parser_cache = {}
