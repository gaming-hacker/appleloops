import logging

from . import disk
from . import ARGS

LOG = logging.getLogger(__name__)
PKG_SERVER_IS_DMG = True if ARGS.pkg_server and str(ARGS.pkg_server).endswith('.dmg') else False


def generate(packages):
    """Generates statistics about packages"""
    # Generate statistics for display
    mandatory_count = len([pkg for pkg in packages if pkg.mandatory and not pkg.installed]) if ARGS.deployment else len([pkg for pkg in packages if pkg.mandatory])
    optional_count = len([pkg for pkg in packages if not pkg.mandatory and not pkg.installed]) if ARGS.deployment else len([pkg for pkg in packages if not pkg.mandatory])
    mandatory_dld_size = sum([pkg.download_size for pkg in packages if pkg.mandatory])
    optional_dld_size = sum([pkg.download_size for pkg in packages if not pkg.mandatory])
    mandatory_inst_size = sum([pkg.installed_size for pkg in packages if pkg.mandatory and not pkg.installed])
    optional_inst_size = sum([pkg.installed_size for pkg in packages if not pkg.mandatory and not pkg.installed])

    # Message strings
    count_msg = list()  # Join with ' and '.join()
    mand_msg = '{mand} mandatory packages'.format(mand=mandatory_count)
    optn_msg = '{optn} optional packages'.format(optn=optional_count)

    if mandatory_count > 0:
        if ARGS.deployment:
            if PKG_SERVER_IS_DMG:
                mand_msg = '{msg} to install ({inst_size})'.format(msg=mand_msg, inst_size=disk.convert(mandatory_inst_size))
            else:
                mand_msg = '{msg} to download ({dld_size}) and install ({inst_size})'.format(msg=mand_msg,
                                                                                             dld_size=disk.convert(mandatory_dld_size),
                                                                                             inst_size=disk.convert(mandatory_inst_size))
        else:
            mand_msg = '{msg} to download ({dld_size})'.format(msg=mand_msg, dld_size=disk.convert(mandatory_dld_size))

    if optional_count > 0:
        if ARGS.deployment:
            if PKG_SERVER_IS_DMG:
                optn_msg = '{msg} to install ({inst_size})'.format(msg=optn_msg, inst_size=disk.convert(optional_inst_size))
            else:
                optn_msg = '{msg} to download ({dld_size}) and install ({inst_size})'.format(msg=optn_msg,
                                                                                             dld_size=disk.convert(optional_dld_size),
                                                                                             inst_size=disk.convert(optional_inst_size))
        else:
            optn_msg = '{msg} to download ({dld_size})'.format(msg=optn_msg, dld_size=disk.convert(optional_dld_size))

    count_msg.append(mand_msg)
    count_msg.append(optn_msg)
    status_msg = 'Discovered {msg}'.format(msg=' and '.join(count_msg))

    LOG.info(status_msg)
