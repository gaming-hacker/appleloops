#!/usr/bin/env python3
'''Build distributable and package.'''
import argparse
import re
import subprocess
import sys
import zipapp

import yaml

from datetime import datetime
from pathlib import Path, PurePath

CONF = PurePath(Path.cwd(), 'src/loopslib/resources/configuration.yaml')


def arguments():
    """Construct arguments."""
    result = None
    parser = argparse.ArgumentParser()

    parser.add_argument('-p', '--python',
                        dest='python',
                        metavar='[path]',
                        help='specify path to use as shebang line',
                        default='/usr/bin/env python3',
                        required=False)

    parser.add_argument('-s', '--source',
                        dest='source',
                        metavar='[path]',
                        help='specify path to use as source folder for zippapp file',
                        default=str(PurePath(Path.cwd(), 'src')),
                        required=False)

    # Directory for building a package to. Internal use only.
    parser.add_argument('--pkg-dir',
                        dest='pkg_dir',
                        metavar='[path]',
                        help=argparse.SUPPRESS,
                        default=str(PurePath(Path.cwd(), 'build/pkg')),
                        required=False)

    # Root directory for package building. Internal use only.
    parser.add_argument('--pkg-root',
                        dest='pkg_root',
                        metavar='[path]',
                        help=argparse.SUPPRESS,
                        default=str(PurePath(Path.cwd(), 'dist')),
                        required=False)

    parser.add_argument('--sign-pkg',
                        dest='sign',
                        metavar='[certificate]',
                        help=('specify a signing certificate for signing the package. '
                              'Ex: "Developer ID Installer: appleloops (E1NP66G7X1)"'),
                        required=False)

    parser.add_argument('--check-updates',
                        dest='check_updates',
                        action='store_true',
                        help='check for new source content property lists',
                        required=False)

    parser.add_argument('--update-version',
                        dest='update_version',
                        action='store_true',
                        help='updates the version and build',
                        default=False,
                        required=False)

    parser.add_argument

    result = parser.parse_args()

    return result


def build_package(config, zipsource, shebang, pkgroot, dest, signing_cert=None):
    """Builds a deployable package. Returns the file path of the resulting package."""
    result = None
    bundle_id = config['MODULE']['bundle_id']
    package_title = config['MODULE']['name']
    version = config['MODULE']['version']
    component = Path(PurePath(dest, '{title}-{version}.component.pkg'.format(title=package_title, version=version)))
    package = Path(PurePath(dest, '{title}-{version}.pkg'.format(title=package_title, version=version)))
    zipfile = Path(PurePath(pkgroot, 'usr/local/bin/{title}'.format(title=package_title)))

    zipapp.create_archive(source=zipsource, target=zipfile, interpreter=shebang, compressed=True)

    if not Path(dest).exists():
        Path(dest).mkdir(parents=True, exist_ok=True)

    pkgbuild = ['/usr/bin/pkgbuild', '--root', pkgroot,
                '--filter', '.DS_Store',
                '--filter', '__pycache__',
                '--identifier', bundle_id,
                '--version', version,
                '--ownership', 'recommended',
                '--preserve-xattr', str(component)]

    productbuild = ['/usr/bin/productbuild', '--identifier', bundle_id,
                    '--package', str(component), str(package)]

    if signing_cert:
        productbuild.insert(3, '--sign')
        productbuild.insert(4, signing_cert)

    _pkgbuild = subprocess.run(pkgbuild, capture_output=True, encoding='utf-8')

    if _pkgbuild.returncode == 0:
        print(_pkgbuild.stdout.strip())
    else:
        print(_pkgbuild.stderr)

        component.unlink(missing_ok=True)
        sys.exit(_pkgbuild.returncode)

    _productbuild = subprocess.run(productbuild, capture_output=True, encoding='utf-8')

    if _productbuild.returncode == 0:
        print(_productbuild.stdout.strip())
    else:
        print(_productbuild.stderr.strip())

        component.unlink(missing_ok=True)
        sys.exit(_productbuild.returncode)

    if package.exists():
        result = package
        component.unlink(missing_ok=True)

    return result


def read_config(y=CONF):
    """Get configuration."""
    result = None

    with open(CONF, 'r') as _f:
        result = yaml.safe_load(_f)

    return result


def status(u):
    """Status code of an HTTP/HTTPS resource"""
    result = None

    # Convert URL from path object to string if path
    if isinstance(u, (Path, PurePath)):
        u = str(u)

    cmd = ['/usr/bin/curl', '-I', '-L', '--silent', '-o', '/dev/null', '-w', '"%{http_code}"', '--user-agent', 'appleloops-update-check', u]
    _p = subprocess.run(cmd, capture_output=True, encoding='utf-8')
    result = int(_p.stdout.strip().replace('"', ''))

    return result


def update_supported_sources(config, http_ok, feed_url):
    """Update the supported source files. Returns a tuple indicating version/build update required, and a modified config."""
    result = (False, config)  # Tuple, ('update_version', 'config')
    apps = ['garageband', 'logicpro', 'mainstage']
    update_version = False

    for app in apps:
        sources = config['AUDIOCONTENT']['supported'][app]
        ver_reg = re.compile(r'\d+')
        latest_ver = int(sorted([re.findall(ver_reg, _v)[0] for _k, _v in sources.items()], reverse=True)[0]) + 1
        future_ver = latest_ver + 11

        for ver in range(latest_ver, future_ver):
            new_plist = '{app}{ver}.plist'.format(app=app, ver=ver)
            url = '{feedurl}/{sourcefile}'.format(feedurl=feed_url, sourcefile=new_plist)
            plist_name = '{app}{ver}'.format(app=app, ver=ver)

            print('Checking {url}'.format(url=url))

            if status(url) in http_ok:
                update_version = True
                config['AUDIOCONTENT']['supported'][app][plist_name] = new_plist

                print('Adding new supported source \'{app}:{source}\''.format(app=app, source=new_plist))

    # Update the config file with relevant changes
    if update_version:
        print('Updating configuration file with new supported source files.')

        with open(CONF, 'w') as _f:
            yaml.dump(config, _f)

    # app = list({re.sub(app_reg, '', _v) for _, _v in sources.items()})[0]
    # app_reg = re.compile(r'\d+.plist')

    result = (update_version, config)

    return result


def update_version(config, new_version=None, new_build=None):
    """Updates the minor version by 1 and sets the build to the current date."""
    old_version = config['MODULE']['version']
    build_date = datetime.now().strftime('%Y-%m-%d') if not new_build else new_build
    major, minor, patch = old_version.split('.')
    patch = str(int(patch) + 1)
    new_version = '{major}.{minor}.{patch}'.format(major=major, minor=minor, patch=patch) if not new_version else new_version

    config['MODULE']['version'] = new_version
    config['MODULE']['build_date'] = build_date

    print('Updating version from {old} to {new}, updating build to {build}'.format(old=old_version, new=new_version, build=build_date))

    with open(CONF, 'w') as _f:
        yaml.dump(config, _f)


def main():
    """main"""
    args = arguments()
    config = read_config()
    feed_url = config['AUDIOCONTENT']['feed_url']
    http_ok = config['CURL']['http_ok_status']
    update_ver = args.update_version  # Defaults to false

    # Do any updates first
    if args.check_updates:
        update_ver, config = update_supported_sources(config=config, http_ok=http_ok, feed_url=feed_url)

    # Update the version/build if required.
    if update_ver:
        update_version(config=config)

    build_package(config=config, zipsource=args.source, shebang=args.python, pkgroot=args.pkg_root, dest=args.pkg_dir, signing_cert=args.sign)


if __name__ == '__main__':
    main()
