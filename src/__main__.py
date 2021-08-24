import logging

from sys import exit

from loopslib import dmg
from loopslib import process
from loopslib import stats
from loopslib import ARGS

LOG = logging.getLogger(__name__)


try:
    if ARGS.compare:
        process.compare_sources()

    # Empty vars
    deployment_dmg, sparseimage, mount_vol, device, packages = (None, None, None, None, set())

    # Mount the DMG early if in deployment mode to ensure paths exist when processing packages
    if ARGS.deployment:
        # Mount a DMG if a DMG has been specified as a the package mirror source
        deployment_dmg = process.mount_pkgsrv_dmg()

    # Creates a sparse image if building a DMG
    if not ARGS.deployment and ARGS.build_dmg:
        sparseimage, mount_vol, device = process.init_dmg()

    # Set up app object instances and packages set.
    garageband, logicpro, mainstage, packages = process.apps_plists()

    # If packages exist, process them.
    if packages:
        # Generate statistics
        stats.generate(packages)

        # Do freespace checks, exits if not enough space.
        has_freespace, drive_dest = process.freespace_checks(packages)

        # Download or install
        process.download_install(packages)

        # Unmount the package server DMG
        if deployment_dmg:
            deployment_dmg = dmg.eject()

        # Convert sparseimage to DMG if creating a DMG
        if sparseimage:
            process.convert_sparse(s=sparseimage)
    else:
        if not ARGS.deployment:
            LOG.info('No packages to download.')
        else:
            LOG.info('No packages to download/install.')

    # Clean up
    process.cleanup()
except KeyboardInterrupt:
    # Clean up
    LOG.info('\nKeyboard Interrupt signal received.')
    process.cleanup()

    exit(22)
