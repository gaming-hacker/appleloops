import argparse
import logging

from . import argchecks
from . import resource
from . import VERSION_STRING

LOG = logging.getLogger(__name__)


def arg_choices(choices):
    """Return a dictionary of choices for specific arguments."""
    result = {'latest': dict(),
              'plists': list(),
              'supported': list()}

    # Choices
    result['supported'] = sorted([app for app, _ in choices.items()])

    # Construct choices for the latest supported source files
    for app in result['supported']:
        result['latest'][app] = sorted([_k for _k, _v in choices[app].items()], reverse=True)[0]

        for _k, _v in choices[app].items():
            result['plists'].append(_v)

    return result


def create(choices):
    """Create command line arguments."""
    result = None
    parser = argparse.ArgumentParser()
    arguments = resource.read('arguments.yaml')
    standard_args = arguments['standard']
    mutually_excl = arguments['mutually_exclusive']
    choices = arg_choices(choices=choices)

    # Process standard arguments that don't have more complex exclusivity
    for argset in standard_args:
        _args = argset['args']
        _kwargs = argset['kwargs']

        # Plists that can be compared
        if '--compare' in _args:
            _kwargs['choices'] = choices['plists']

        # Add version string to use in version output
        if '--version' in _args:
            _kwargs['version'] = VERSION_STRING

        parser.add_argument(*_args, **_kwargs)

    # Process each mutually exclusive set of arguments individually
    mut_excl_prsr = dict()  # Store mutually exclusive parsers for each specific group

    for mex_args, argsets in mutually_excl.items():
        mut_excl_prsr[mex_args] = parser.add_mutually_exclusive_group()

        for argset in argsets:
            _args = argset['args']
            _kwargs = argset['kwargs']

            # Add specific choice options
            if '--apps' in _args in _args:
                _kwargs['choices'] = choices['supported']
                _kwargs['choices'].insert(0, 'all')

            if '--fetch-latest' in _args:
                _kwargs['choices'] = choices['supported']
                _kwargs['choices'].insert(0, 'all')

            if '--plists' in _args:
                _kwargs['choices'] = choices['plists']
                _kwargs['choices'].insert(0, 'all')

            mut_excl_prsr[mex_args].add_argument(*_args, **_kwargs)

    result = argchecks.check(args=parser.parse_args(), helper=parser.print_usage, choices=choices)

    return result
