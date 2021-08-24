import logging; logging.getLogger(__name__).addHandler(logging.NullHandler())  # NOQA
import sys
import tempfile

from pathlib import Path
from uuid import uuid4

from . import osinfo

if not osinfo.python_compatible():
    print('Python 3.9.5 is required.')
    sys.exit(1)

_dupe_argv = {_arg: 0 for _arg in sys.argv if _arg.startswith('-') or _arg.startswith('--')}

if len(sys.argv) > 1:
    for arg in sys.argv:
        if arg.startswith('-') or arg.startswith('--'):
            _dupe_argv[arg] += 1

if any([_dupe_argv[arg] > 1 for arg, _ in _dupe_argv.items()]):
    print('Duplicate arguments detected.')
    sys.exit(1)

from . import messages  # NOQA
from . import configuration  # NOQA

silent = any([_arg in ['--silent', '-s'] for _arg in sys.argv])
log_level = 'DEBUG' if any([_arg.lower() == 'debug' for _arg in sys.argv]) else 'INFO'

messages.logging_conf(log_name=__name__, silent=silent, level=log_level)
CONF = configuration.load()
LOG = logging.getLogger(__name__)

BUNDLE_ID = CONF['MODULE']['bundle_id']
NAME = CONF['MODULE']['name']
LICENSE = CONF['MODULE']['license']
VERSION = CONF['MODULE']['version']
BUILD = CONF['MODULE']['build_date']
VERSION_STRING = '{name} {version} ({build}) {eula}'.format(name=NAME, version=VERSION, build=BUILD, eula=LICENSE)
USER_AGENT = '{name}/{version}'.format(name=NAME, version=VERSION)
HTTP_OK = CONF['CURL']['http_ok_status']
PACKAGE_CHOICES = CONF['AUDIOCONTENT']['supported']
BASE_URL = CONF['AUDIOCONTENT']['base_url']
FEED_URL = CONF['AUDIOCONTENT']['feed_url']
HTTP_MIRROR_TEST_PATHS = CONF['AUDIOCONTENT']['mirror_test_paths']
APPLICATION_FOLDER = CONF['APPLICATIONS']['app_folder']
APPLICATIONS = CONF['APPLICATIONS']['supported']
TEMPDIR = Path(tempfile.gettempdir()) / BUNDLE_ID
DMG_MOUNT = CONF['DMG']['mountpoint']
DMG_VOLUME_NAME = CONF['DMG']['volume_name']
VALID_DMG_FS = CONF['DMG']['valid_fs']
DMG_DEFAULT_FS = CONF['DMG']['default_fs']
RUN_UUID = str(uuid4()).upper()
INSTALL_TARGET = Path(CONF['INSTALL']['target'])
FAIL_LOG = 'appleloops_failed_installs.log'
SYSTEM_UPDATER = Path('/{pref}'.format(pref=CONF['UPDATER']['pref']))
USER_UPDATER = Path('~/{pref}'.format(pref=CONF['UPDATER']['pref'])).expanduser()

# Have to do other non-core module loading here to avoid circular imports
from . import arguments  # NOQA

ARGS = arguments.create(choices=PACKAGE_CHOICES)
DMG_DEFAULT_FS = ARGS.apfs_dmg if ARGS.apfs_dmg else DMG_DEFAULT_FS

LOG.warning('Run UUID: {uuid}'.format(uuid=RUN_UUID))
LOG.debug('{args}'.format(args=' '.join(sys.argv)))
LOG.debug('{versionstr}'.format(versionstr=VERSION_STRING))
LOG.debug('macOS {osver} ({osbuild} {arch})'.format(osver=osinfo.version(), osbuild=osinfo.build(), arch=osinfo.arch()))
LOG.debug('{pythonver}'.format(pythonver=osinfo.python_ver()))
LOG.debug('{curlver}'.format(curlver=osinfo.curl_version()))
LOG.debug('Temporary working directory: {tmpdir}'.format(tmpdir=TEMPDIR))
