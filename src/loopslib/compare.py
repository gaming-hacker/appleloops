import difflib
import logging
import sys

from pathlib import Path

from . import disk
from . import source
from . import ARGS

LOG = logging.getLogger(__name__)


def sources(plist_a, plist_b, style=ARGS.compare_style):
    """Compares packages in the specified sources."""
    styles = ['context', 'unified', 'html']

    if style not in styles:
        LOG.info('Invalid diff style selected. Choose from {styles}'.format(styles=styles))
        sys.exit(88)

    packages_a = source.PropertyList(plist=plist_a, comparing=True).packages
    packages_b = source.PropertyList(plist=plist_b, comparing=True).packages

    if packages_a:
        _unsequenced_a = sorted([pkg for pkg in packages_a if not pkg.sequence_number], key=lambda pkg: pkg.download_name)
        _sequenced_a = sorted([pkg for pkg in packages_a if pkg.sequence_number], key=lambda pkg: pkg.sequence_number)
        packages_a = _unsequenced_a + _sequenced_a

    if packages_b:
        _unsequenced_b = sorted([pkg for pkg in packages_b if not pkg.sequence_number], key=lambda pkg: pkg.download_name)
        _sequenced_b = sorted([pkg for pkg in packages_b if pkg.sequence_number], key=lambda pkg: pkg.sequence_number)
        packages_b = _unsequenced_b + _sequenced_b

    if packages_a and packages_b:
        packages_a_strings = ['{pkgname} ({mandatory}, {size})'.format(pkgname=pkg.download_name,
                                                                       mandatory='Mandatory' if pkg.mandatory else 'Optional',
                                                                       size=disk.convert(pkg.download_size)) for pkg in packages_a]

        packages_b_strings = ['{pkgname} ({mandatory}, {size})'.format(pkgname=pkg.download_name,
                                                                       mandatory='Mandatory' if pkg.mandatory else 'Optional',
                                                                       size=disk.convert(pkg.download_size)) for pkg in packages_b]

        if style == 'context':
            diff = difflib.context_diff(packages_a_strings, packages_b_strings, fromfile=plist_a, tofile=plist_b)
        elif style == 'unified':
            diff = difflib.unified_diff(packages_a_strings, packages_b_strings, fromfile=plist_a, tofile=plist_b)
        elif style == 'html':
            output = Path().home() / 'Desktop/{plist1}_{plist2}.html'.format(plist1=plist_a.replace('.plist', ''),
                                                                             plist2=plist_b.replace('.plist', ''))
            differ = difflib.HtmlDiff()
            diff = differ.make_file(packages_a_strings, packages_b_strings, fromdesc=plist_a, todesc=plist_b)

            with open(output, 'w') as _f:
                _f.write(diff)

            if output.exists():
                LOG.info('Diff HTML output to {output}'.format(output=output))

        if style != 'html':
            for line in diff:
                print(line.strip('\n'))

        sys.exit(0)
    else:
        if not packages_a and not packages_b:
            plists = '{plist1} and {plist2}'.format(plist1=plist_a, plist2=plist_b)
        else:
            if not packages_a:
                plists = '{plist1}'.format(plist1=plist_a)

            if not packages_b:
                plists = '{plist1}'.format(plist1=plist_b)

        LOG.info('Could not find packages in {plists}'.format(plists=plists))
        sys.exit(99)
