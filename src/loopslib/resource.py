import logging
import importlib.resources as resources

from . import yaml

LOG = logging.getLogger(__name__)


def read(resource, package='loopslib.resources', **kwargs):
    """Load a YAML resource file (r)."""
    result = dict()
    f = resources.open_text(package=package, resource=resource)

    # This addresses an issue where dealing with a python 'str' type fails
    # yaml.constructor.ConstructorError: could not determine a constructor for the
    # tag 'tag:yaml.org,2002:python/name:builtins.str'
    if resource == 'arguments.yaml':
        result = yaml.load(f, Loader=yaml.Loader)
    else:
        result = yaml.safe_load(f)

    f.close()

    LOG.debug('Read resource file {package}/{resource}'.format(package=package.replace('.', '/'), resource=resource))

    return result
