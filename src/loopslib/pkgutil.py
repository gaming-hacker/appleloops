import logging
import subprocess

from pathlib import Path

from . import plist
from . import versions

LOG = logging.getLogger(__name__)


def info(i):
    """Returns output of '/usr/sbin/pkgutil'"""
    result = dict()
    cmd = ['/usr/sbin/pkgutil', '--pkg-info-plist', i]
    _p = subprocess.run(cmd, capture_output=True)  # leave output as bytes for plist string read

    if _p.returncode == 0:
        result = plist.read_string(_p.stdout)
        LOG.debug(result)
    else:
        LOG.debug(_p.stderr.decode('utf-8').strip())

    return result


def pkg_version(i):
    """Return package version if installed, returns LooseVersion."""
    return versions.convert(info(i).get('pkg-version', None))


def is_installed(files, lcl_ver, pkg_ver):
    """Determine if package is installed, returns boolean."""
    result = False

    if files:
        if isinstance(files, (set, list)) and len(files) == 1:
            files = Path(files[0]).exists()
        elif isinstance(files, (set, list)) and len(files) > 1:
            files = any([Path(_f).exists() for _f in files])
        elif isinstance(files, str):
            files = Path(files).exists()
        elif not files:
            files = False

        lcl_ver = versions.convert(lcl_ver)
        pkg_ver = versions.convert(pkg_ver)

    result = files and lcl_ver > pkg_ver

    return result


def upgrade_pkg(lcl_ver, pkg_ver):
    """Determine if package should be upgrade, returns boolean."""
    result = False

    # If local version is '0.0.0' this is most likely because it isn't installed
    if lcl_ver != '0.0.0':
        result = versions.convert(lcl_ver) < versions.convert(pkg_ver)

    return result
