import logging
import re
import subprocess

from pathlib import Path, PurePath
from urllib.parse import urlparse

from . import curl
from . import messages
from . import pkgutil
from . import versions
from . import ARGS
from . import DMG_MOUNT
from . import FAIL_LOG
from . import FEED_URL
from . import INSTALL_TARGET
from . import RUN_UUID

PKG_SERVER_IS_DMG = True if ARGS.pkg_server and str(ARGS.pkg_server).endswith('.dmg') else False
LOG = logging.getLogger(__name__)
FAILED = messages.logging_conf(log_name='failedinstalls', silent=True, level='WARNING', log_file=FAIL_LOG)
FAILED.warning('Run UUID: {uuid}'.format(uuid=RUN_UUID))
FAILED.warning(ARGS)


class LoopPackage:
    """Package object"""
    INSTANCES = set()  # Track created instances

    def __init__(self, **kwargs):
        self.package_id = kwargs.get('PackageID', None)
        self.download_name = kwargs.get('DownloadName', None)
        self.file_check = kwargs.get('FileCheck', None)
        self.installed_size = kwargs.get('InstalledSize', None)
        self.mandatory = kwargs.get('IsMandatory', False)
        self.version = versions.convert(kwargs.get('PackageVersion', '0.0.0'))

        # Modify Apple attributes
        self.package_id = self.package_id.replace('. ', '') if self.package_id else None  # Apple typo fix

        if self.installed_size:
            if not isinstance(self.installed_size, (int, float)):
                self.installed_size = float(self.installed_size)

        # Set custom attributes
        self.installed_version = pkgutil.pkg_version(self.package_id) if self.package_id else None
        self.installed = pkgutil.is_installed(self.file_check, self.installed_version, self.version)
        self.upgrade = pkgutil.upgrade_pkg(self.installed_version, self.version)
        self.url = self.parse_url(self.download_name)
        self.download_dest = self.parse_dest(self.url)
        self.download_size, self.download_resume, self.cdn_uuid = self.parse_headers(self.url)
        self.badwolf_ignore = False
        self.status = self.parse_http_status(self.url)
        self.download_name = str(PurePath(self.download_name).name)  # Make the download name friendly
        self.sequence_number = self.parse_seq_number(self.download_name)

        # Set installed/upgrade values if force is required
        if ARGS.force:
            self.installed = False
            self.upgrade = False

        # Add self.package_id to INSTANCES tracker
        self.__class__.INSTANCES.add(self.package_id)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        else:
            return NotImplemented

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return not self.__dict__ == other.__dict__
        else:
            return NotImplemented

    def __hash__(self):
        if isinstance(self, self.__class__):
            return hash(self.package_id)
        else:
            return NotImplemented

    def _regex_parse_string(self, s):
        """Parses a url/path to fix the folder path"""
        result = None
        reg = re.compile(r'lp10_ms3_content_2016/../lp10_ms3_content_2013')
        swap = 'lp10_ms3_content_2013'
        result = re.sub(reg, swap, s)

        return result

    def parse_http_status(self, u):
        """Parse the HTTP status, returns an int"""
        result = 0

        if ARGS.deployment:
            if urlparse(u).scheme:
                result = curl.status(u)
            elif PKG_SERVER_IS_DMG:
                if Path(u).exists():
                    result = 200
                else:
                    result = 404

                LOG.debug('Set HTTP status to {status} for local path'.format(status=result))
        else:
            result = curl.status(u)

        return result

    def parse_headers(self, u):
        """Parse information from headers, returns an tuple containing size, resume, CDN UUID"""
        result = None
        headers = dict()
        size, resume, cdn_uuid = 0, False, None

        if urlparse(u).scheme:
            headers = curl.headers(self.url)
            size = headers.get('content-length', 0)
            resume = headers.get('accept-ranges', False) == 'bytes' or False
            cdn_uuid = headers.get('cdnuuid', None)

        if ARGS.deployment and PKG_SERVER_IS_DMG and Path(u).exists():
            size = Path(u).stat().st_size
            LOG.debug('Download size set to local path file size {size}'.format(size=size))

        result = (size, resume, cdn_uuid)

        return result

    def parse_seq_number(self, p):
        """Parse out a sequence number from the package name"""
        result = None
        reg = re.compile(r'_\d+_')

        if re.findall(reg, p):
            result = int(re.findall(reg, p)[0].replace('_', ''))

        return result

    def parse_url(self, n):
        """Parse a URL to use for downloading."""
        result = None
        url = '{feedurl}/{pkgname}'.format(feedurl=FEED_URL, pkgname=n)
        url = self._regex_parse_string(url)
        _url = url
        LOG.debug('Set package URL to {url}'.format(url=url))

        # Change the URL if cache server is specified
        if ARGS.cache_server:
            url = urlparse(url)
            url = '{cachesrv}{urlpath}?source={urlnetloc}'.format(cachesrv=ARGS.cache_server,
                                                                  urlpath=url.path,
                                                                  urlnetloc=url.netloc)

        # Change the URL if package server is specified
        if ARGS.pkg_server:
            if '.dmg' not in str(ARGS.pkg_server):
                # Modifies the existing Apple url to the package server url by combining urlparse attributes
                apple_server = urlparse(url)
                pkg_server = urlparse(str(ARGS.pkg_server))
                pkg_path = '{path}{apple_path}'.format(path=pkg_server.path, apple_path=apple_server.path)
                url = '{scheme}://{netloc}{path}'.format(scheme=pkg_server.scheme, netloc=pkg_server.netloc, path=pkg_path)
            elif '.dmg' in str(ARGS.pkg_server):
                LOG.debug('Swapping packge URL to download name attribute for DMG based deployment')
                apple_server = urlparse(url)
                if ARGS.flat_mirror:
                    url = '{dmg_mount}{path}'.format(dmg_mount=DMG_MOUNT, path=PurePath(apple_server.path).name)
                else:
                    url = '{dmg_mount}{path}'.format(dmg_mount=DMG_MOUNT, path=apple_server.path)

        # Only log the URL update if the url differs
        if url != _url:
            LOG.debug('Updated package URL to {url}'.format(url=url))

        result = url

        return result

    def parse_dest(self, u):
        """Parse a download destination."""
        result = None
        # Setting destination here avoids issues where disk space checks would fail if
        # downloading to a DMG as the sparseimage will have no space, but the drive
        # the sparseimage is stored on will have the space.
        destination = DMG_MOUNT if ARGS.build_dmg else ARGS.destination

        if ARGS.flat_mirror:
            dest = '{dest}/{pkgname}'.format(dest=destination, pkgname=PurePath(u).name)
        else:
            dest = '{dest}/{pkgname}'.format(dest=destination, pkgname=urlparse(u).path.lstrip('/'))

        if ARGS.deployment:
            if ARGS.pkg_server:
                if PKG_SERVER_IS_DMG:
                    dest = self.url

                    if ARGS.flat_mirror:
                        dest.replace(str(ARGS.destination), DMG_MOUNT).replace('lp10_ms3_content_2016/', '').replace('lp10_ms3_content_2013/', '')
                else:
                    dest = '/tmp/appleloops/{package}'.format(package=PurePath(u).name)

        result = Path(self._regex_parse_string(dest))

        return result

    def install(self):
        """Install package, returns a tuple with the process returncode at [0] and success/error message at [1]"""
        result = None
        cmd = ['/usr/sbin/installer', '-dumplog', '-pkg', str(self.download_dest), '-target', str(INSTALL_TARGET)]

        # Insert the untrusted flag into the correct part of the install command
        if ARGS.unsigned:
            cmd.insert(1, '-allowUntrusted')

        if not ARGS.dry_run:
            LOG.debug(' '.join([str(x) for x in cmd]))
            _pfx = 'Upgraded' if self.upgrade else 'Installed'
            _p = subprocess.run(cmd, capture_output=True, encoding='utf-8')

            if _p.returncode == 0:
                result = (_p.returncode, '{prefix} {pkg}'.format(prefix=_pfx, pkg=self.package_id))
                LOG.debug(_p.stdout.strip())
            else:
                _pfx = 'upgrade' if self.upgrade else 'install'
                _lp = '\'/var/log/install.log\''
                result = (_p.returncode, 'Failed to {prefix} {pkg} - check {log}'.format(prefix=_pfx,
                                                                                         pkg=self.package_id,
                                                                                         log=_lp))
                LOG.debug(_p.stderr.strip())

                FAILED.warning('{pkgname} - source: {pkgurl}'.format(pkgname=self.download_name,
                                                                     pkgurl=self.url))
                FAILED.warning('{pkgname} - dest: {pkgdest}'.format(pkgname=self.download_name,
                                                                    pkgdest=self.download_dest))
                FAILED.warning('{pkgname} - {installerror}'.format(pkgname=self.download_name,
                                                                   installerror=_p.stderr.strip()))

        return result
