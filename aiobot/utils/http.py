import base64

from binascii import Error as BinasciiError

# Из Django - utils.http


def urlsafe_base64_encode(s):
    """
    Encode a bytestring to a base64 string for use in URLs. Strip any trailing
    equal signs.
    """
    return base64.urlsafe_b64encode(s).rstrip(b'\n=').decode('ascii')


def urlsafe_base64_decode(s):
    """
    Decode a base64 encoded string. Add back any trailing equal signs that
    might have been stripped.
    """
    s = s.encode()
    try:
        return base64.urlsafe_b64decode(s.ljust(len(s) + len(s) % 4, b'='))
    except (LookupError, BinasciiError) as e:
        raise ValueError(e)
