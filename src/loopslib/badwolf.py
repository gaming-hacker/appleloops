import logging

from pathlib import Path, PurePath
from pprint import pformat

from . import package
from . import resource
from . import ARGS
from . import PACKAGE_CHOICES

LOG = logging.getLogger(__name__)


def read():
    """Read patch file (pf) for package attribute patching from specific source (source)."""
    result = resource.read(resource='badwolf.yaml')

    return result


def patch(packages, source, comparing=False):
    """Patch the set of packages with any updates"""
    result = set()
    sources = dict()

    if ARGS.packages:
        _packages = {_pkg: _attrs for _pkg, _attrs in packages.items()}
    else:
        _packages = {_pkg: _attrs for _pkg, _attrs in packages.items()
                     if (ARGS.mandatory and _attrs.get('IsMandatory', False)) or (ARGS.optional and not _attrs.get('IsMandatory', False))}

    for app in PACKAGE_CHOICES:
        sources.update({_k: _v for _k, _v in PACKAGE_CHOICES[app].items()})

    # Convert either a Path/str instance to a PurePath instance
    # and get the basename of the source in the event the source
    # is a URL or filepath or a string of a filepath.
    if isinstance(source, (Path, str)):
        source = str(PurePath(source).name)

    # Map to valid sources if it doesn't end with '.plist'
    if source in sources and not source.endswith('.plist'):
        source = sources[source]

    # Raises an IndexError if the source is not a valid source
    if source.endswith('.plist'):
        if source not in [_v for _, _v in sources.items()]:
            LOG.info('{source} property list for patching is not a valid source.'.format(source=source))
            raise IndexError

    # Read the patch info from the badwolf yaml and get the relevant source patches
    patches = read().get(source, dict())

    # Total packages (total) and counter (counter)
    total, counter = len([_p for _p in _packages]), 1
    LOG.info('Processing {source}'.format(source=source))

    # Iterate and patch
    for _pkg, _attrs in _packages.items():
        patch = dict()
        ignore = False
        padded_count = '{i:0{width}d}'.format(width=len(str(total)), i=counter)
        package_id = _attrs.get('PackageID', None)

        LOG.warning('Processing {pkg} ({count} of {total})'.format(pkg=_pkg, count=padded_count, total=total))

        if ARGS.ignore_patches:
            new_attrs = _attrs.copy()
        elif not ARGS.ignore_patches:
            patch = patches.get(_pkg, None)
            new_attrs = _attrs.copy()

            if patch:
                LOG.debug('Original {pkg}:\n{attrs}'.format(pkg=_pkg, attrs=pformat(new_attrs)))
                new_attrs.update(patch)
                ignore = patch.get('BadWolfIgnore', False)
                LOG.debug('Patched {pkg}:\n{attrs}'.format(pkg=_pkg, attrs=pformat(new_attrs)))

        # Update the package id
        package_id = new_attrs.get('PackageID', None)

        # If comparing sources, create an instance of package.LoopPackage regardless
        if comparing:
            pkg = package.LoopPackage(**new_attrs)
            LOG.debug('{attrs}'.format(attrs=pkg.__dict__))
            result.add(pkg)
        else:
            if package_id not in package.LoopPackage.INSTANCES:
                pkg = package.LoopPackage(**new_attrs)
                LOG.debug('{attrs}'.format(attrs=pkg.__dict__))

                if not ignore:
                    result.add(pkg)
                    LOG.debug('Added {pkg}'.format(pkg=_pkg))
                else:
                    LOG.debug('Skipped adding {pkg} as it has been patched to be ignored.'.format(pkg=_pkg))
            elif package_id in package.LoopPackage.INSTANCES:
                LOG.debug('Already processed {pkg}'.format(pkg=_pkg))

        _msg = 'Processed ({count} of {total}) - {pkgid}'.format(pkgid=package_id, count=padded_count, total=total)
        counter += 1

        # Add an extra line in the debug output for readability
        if counter - 1 != total:
            _msg = '{msg}\n'.format(msg=_msg)

        LOG.debug(_msg)

    return result
