import logging
import os

from collections import namedtuple
from pathlib import Path, PurePath

LOG = logging.getLogger(__name__)


def convert(b):
    """Converts bytes to human readable value"""
    result = None
    suffixes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    counter = 0
    while b > 1024 and counter < 5:
        counter += 1
        b = b / 1024.0
    suffix = suffixes[counter]
    result = '{0:.2f}'.format(b)
    result = result.replace('.0', '') if result.endswith('.0') else result
    result = result.replace('.00', '') if result.endswith('.00') else result
    result = '{size} {suffix}'.format(size=result, suffix=suffix)
    return result


def statvfs(p):
    """Calculate total free bytes for a given path."""
    result = 0

    if not isinstance(p, (Path, PurePath)):
        p = Path(p)

    # Find the first path that exists, because 'appleloops'
    # may not exist until the first package is downloaded
    while not p.exists():
        p = Path(PurePath(p).parent)

    p = str(p.expanduser())
    s = os.statvfs(p)

    # f_frsize (fundamental file system block size)
    # f_bfree (total number of free blocks)
    # f_frsize * f_bfree = bytes free
    result = s.f_frsize * s.f_bfree

    return result


def freespace(d):
    """Freespace available on specified destination, returns namedtuple (bytes, hr)"""
    result = None
    Result = namedtuple('Result', ['bytes', 'hr'])

    b = statvfs(p=d)
    hr = convert(b)
    result = Result(b, hr)

    return result
