import json

from lxml import html

from urllib.parse import urlparse


def get_host_from_url(url):
    url_struct = urlparse(url)
    host = '%s://%s' % (url_struct.scheme, url_struct.netloc)
    return host


def get_jsondata_from_html(content, key,
                           set_type_script=False):
    """"""
    tree = html.fromstring(content)
    if set_type_script:
        scripts_find = tree.xpath("//script[@type='text/javascript']/text()")
    else:
        scripts_find = tree.xpath("//script/text()")

    for item in scripts_find:
        idx = item.find(key)
        if idx == -1:
            continue
        cut_script_text = item[idx+len(key):]
        idx_open_bkt = cut_script_text.find("{")
        idx_close_bkt = cut_script_text.find("};")
        if idx_open_bkt != -1 and idx_close_bkt != -1:
            script_text = cut_script_text[idx_open_bkt:idx_close_bkt+1]
            return json.loads(script_text)


def get_text_from_area(text, key,
                       open_sym="{",
                       close_sym="};",
                       with_sym=True
                       ):
    """"""
    idx = text.find(key)
    if idx == -1:
        return
    text = text[idx+len(key):]
    idx_open = text.find(open_sym)
    if idx_open == -1:
        return

    idx_open_after = idx_open + len(open_sym)
    idx_close = text[idx_open_after:].find(close_sym)
    if idx_close != -1:
        if with_sym:
            return text[idx_open:idx_open_after+idx_close+1]
        else:
            return text[idx_open+1:idx_open_after+idx_close]


def find_key(data, key_find, key_path=''):
    """
    Поиск нужного ключа в многоуровневой структуре,
    печатает путь из ключей
    """
    if isinstance(data, dict):
        keys = data.keys()
        for key in keys:
            if (key == key_find):
                print(key_path)
                break
            find_key(data[key], key_find, key_path + '.' + key)
    elif isinstance(data, list):
        for item in data:
            find_key(item, key_find, key_path)
