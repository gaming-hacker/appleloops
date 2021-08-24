import logging
import re
import sys

from pathlib import Path
from urllib.parse import urlparse

from . import curl
from . import osinfo
from . import updater
from . import HTTP_OK
from . import HTTP_MIRROR_TEST_PATHS

LOG = logging.getLogger(__name__)


def error(msg, helper, fatal=False, returncode=1):
    _prefix = '{name}: error: argument'.format(name=sys.argv[0])

    helper(sys.stderr)
    LOG.error('{prefix} {msg}'.format(prefix=_prefix, msg=msg))

    if fatal:
        sys.exit(returncode)


def check(args, helper, choices):
    """Check arguments for specific conditions"""
    PKG_SERVER_IS_DMG = True if args.pkg_server and str(args.pkg_server).endswith('.dmg') else False
    latest_plists = ['{choice}.plist'.format(choice=c) for _, c in choices['latest'].items() if c != 'all']
    update_latest_plists = {_k: _v for _k, _v in choices['latest'].items() if _k != 'all'}

    # Deployment - must be root
    if args.deployment:
        if not osinfo.isroot() and not args.dry_run:
            LOG.error('You must be root to run in deployment mode.')
            sys.exit(66)

        # If no apps are specified, then default to all of them and process.
        if not args.apps:
            args.apps = [c for c in choices['supported'] if c != 'all']

    # Must provide 'mandatory' or 'optional' package set
    if not (args.mandatory or args.optional) and not args.packages:
        error(msg='-m/--mandatory or -o/--optional or both are required', fatal=True, helper=helper, returncode=60)

    # APFS DMG requires build
    if args.apfs_dmg and not args.build_dmg:
        error(msg='--APFS: not allowed without argument -b/--build-dmg', fatal=True, helper=helper, returncode=59)

    # Valid Caching Server URL
    if args.cache_server:
        url = urlparse(args.cache_server)

        if not url.port:
            error(msg='-c/--cache-server: requires a port number in http://example.org:556677 format', fatal=True,
                  helper=helper, returncode=58)

        if not url.scheme == 'http':
            error(msg='-c/--cache-server: https is not supported', fatal=True, helper=helper, returncode=57)

    # Specific package mirror options
    if args.pkg_server:
        http_ok = [s for s in HTTP_OK]
        http_ok.append(403)
        http_schemes = ['http', 'https']
        args.pkg_server = args.pkg_server.rstrip('/')
        url = urlparse(args.pkg_server)

        # Only do a status check if url scheme
        if url.scheme and url.scheme in http_schemes:
            status = curl.status(args.pkg_server)
        else:
            status = None

        # Correct scheme
        if url.scheme and url.scheme not in http_schemes:
            error(msg='--pkg-server: HTTP/HTTPS scheme required', fatal=True, helper=helper, returncode=56)

        # If the pkg server is not a DMG
        if not PKG_SERVER_IS_DMG:
            # Test the mirror has either of the expected mirroring folders per Apple servers
            if not any([curl.status('{mirror}/{testpath}'.format(mirror=args.pkg_server, testpath=_p)) in http_ok
                        for _p in HTTP_MIRROR_TEST_PATHS]):

                _test_paths = ["'{pkgsrv}/{p}'".format(pkgsrv=args.pkg_server, p=_p) for _p in HTTP_MIRROR_TEST_PATHS]
                _msg = ('--pkg-server: mirrored folder structure cannot be found, please ensure packages exist in '
                        '{testpaths}'.format(testpaths=', and/or '.join(_test_paths)))
                error(msg=_msg, fatal=True, helper=helper, returncode=55)
        elif PKG_SERVER_IS_DMG:
            # Test if the supplied DMG path exists
            if not url.scheme:
                args.pkg_server = Path(args.pkg_server)

                if not args.pkg_server.exists():
                    error(msg='--pkg-server: path does not exist', fatal=True, helper=helper, returncode=54)
            elif url.scheme:
                if curl.status(args.pkg_server) not in http_ok:
                    error(msg='--pkg-server: path does not exist', fatal=True, helper=helper, returncode=54)

        # Reachability check for http/https
        if status:
            if status and status not in http_ok:
                error(msg='--pkg-server: HTTP {status} for specified URL'.format(status=status), fatal=True,
                      helper=helper, returncode=53)

    # Convert items that should be file paths to Path objects
    if args.destination:
        args.destination = Path(args.destination)

    # Build DMG - also set the destination to be the DMG
    if args.build_dmg:
        args.build_dmg = Path(args.build_dmg)

    # Handle all apps
    if args.apps and 'all' in args.apps:
        args.apps = [c for c in choices['supported'] if c != 'all']

    # Handle all plists
    if args.plists and 'all' in args.plists:
        args.plists = ['{choice}.plist'.format(choice=c) for _, c in choices['latest'].items() if c != 'all']

    # Handle fetch latest
    if args.fetch_latest:
        if 'all' in args.fetch_latest:
            args.plists = ['{choice}'.format(choice=c) for c in latest_plists]
        else:
            args.plists = ['{plist}.plist'.format(plist=update_latest_plists[app]) for app in args.fetch_latest]

        # Do an update check
        plists = updater.check(apps=args.plists, latest=update_latest_plists)
        args.plists = ['{plist}.plist'.format(plist=_v) for _, _v in plists.items()]

    # Handle individual package downloads by setting args.plists to all plists for searchability.
    if args.packages:
        args.plists = [c for c in choices['plists'] if c != 'all']
        args.ignore_patches = True
        args.force = True

    # Sort args.plists into reverse order so newewst releases are handled first
    if args.plists:
        # sort the plists by name first, then version
        gb = sorted([p for p in args.plists if p.startswith('garageband')], reverse=True)
        lp = sorted([p for p in args.plists if p.startswith('logicpro')], reverse=True)
        ms = sorted([p for p in args.plists if p.startswith('mainstage')], reverse=True)

        args.plists = gb + lp + ms

    # Handle comparisons
    if args.compare:
        args.compare = sorted(args.compare)  # Sort so oldest is first, newest is last
        reg = re.compile(r'\d+.plist')
        prefix_a = re.sub(reg, '', args.compare[0])
        prefix_b = re.sub(reg, '', args.compare[1])
        args.compare_style = 'unified' if not args.compare_style else args.compare_style  # Sets default to a git diff like output

        if prefix_a != prefix_b:
            error(msg='--compare: cannot compare property lists for different applications', fatal=True, helper=helper, returncode=52)

    # Handle style of comparison
    if args.compare_style and not args.compare:
        error(msg='--compare-style: not allowed without argument --compare', fatal=True, helper=helper, returncode=51)

    result = args

    return result
