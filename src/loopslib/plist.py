import plistlib


def read(f):
    """Read Property List"""
    result = None

    with open(f, 'rb') as _f:
        result = plistlib.load(_f)

    return result


def read_string(s):
    """Read Property List from string."""
    result = plistlib.loads(s)

    return result


def write(d, f):
    """Write Property List to file."""
    result = None

    with open(f, 'wb') as _f:
        plistlib.dump(d, _f)
        result = _f

    return result
