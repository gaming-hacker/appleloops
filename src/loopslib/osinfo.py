import subprocess
import sys

from os import geteuid

from . import versions as vers


def arch():
    """Hardware architecture"""
    result = None
    cmd = ['/usr/bin/arch']
    _p = subprocess.run(cmd, capture_output=True, encoding='utf-8')

    if _p.returncode == 0:
        result = _p.stdout.strip()

    return result


def curl_version():
    result = None
    cmd = ['/usr/bin/curl', '--version']
    _p = subprocess.run(cmd, capture_output=True, encoding='utf-8')

    if _p.returncode == 0:
        result = _p.stdout.strip()

    return result


def build():
    """macOS build"""
    result = None
    cmd = ['/usr/bin/sw_vers', '-buildVersion']
    _p = subprocess.run(cmd, capture_output=True, encoding='utf-8')

    if _p.returncode == 0:
        result = _p.stdout.strip()

    return result


def isroot():
    """User is root."""
    result = geteuid() == 0

    return result


def version():
    """macOS version number."""
    # Note: Software version "might" get reported as '10.16' depending on Python used.
    result = None
    cmd = ['/usr/bin/sw_vers', '-productVersion']
    _p = subprocess.run(cmd, capture_output=True, encoding='utf-8')

    if _p.returncode == 0:
        result = vers.convert(_p.stdout.strip())

    return result


def python_ver():
    """Python version."""
    result = 'Python {version}'.format(version=' '.join(sys.version.splitlines()))

    return result


def python_compatible():
    """Check if python version is minimum required."""
    result = False
    req_ver = vers.convert('3.9.5')
    pythonver = vers.convert('{major}.{minor}.{micro}'.format(major=sys.version_info.major,
                                                              minor=sys.version_info.minor,
                                                              micro=sys.version_info.micro))

    result = pythonver >= req_ver

    return result
