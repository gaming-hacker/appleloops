from distutils.version import LooseVersion


def convert(ver=None):
    """Convert a string into a LooseVersion object."""
    # NOTE: Return '0.0.0' if 'ver' is None because LooseVersion can't handle 'None'
    result = LooseVersion('0.0.0')

    if not isinstance(ver, LooseVersion):
        if isinstance(ver, str):
            result = LooseVersion(ver)
        elif isinstance(ver, (float, int)):
            result = LooseVersion(str(ver))
    elif isinstance(ver, LooseVersion):
        result = ver

    return result
