import logging

from pprint import pprint

from . import resource

LOG = logging.getLogger(__name__)


def load():
    """Create command line arguments."""
    result = resource.read('configuration.yaml')

    return result