import logging
import subprocess

from pathlib import Path
from pathlib import PurePath

from . import USER_AGENT

LOG = logging.getLogger(__name__)


def headers(u):
    """Headers of an HTTP/HTTPS resource"""
    result = dict()
    _cmd = ['/usr/bin/curl', '-I', '-L', '--user-agent', USER_AGENT, u]
    _p = subprocess.run(_cmd, capture_output=True, encoding='utf-8')

    if _p.returncode == 0:
        _lines = _p.stdout.strip().splitlines()

        for _l in _lines:
            _l = _l.strip()

            if ': ' in _l:
                _k, _v = _l.split(': ')

                if all([_c.isdigit() for _c in _v]):
                    _v = int(_v)
                else:
                    _v = _v.strip()

                result[_k.lower().strip()] = _v

    LOG.debug('{cmd} [exit code {returncode}]'.format(cmd=' '.join(_cmd), returncode=_p.returncode))
    LOG.debug(result)

    return result


def is_compressed(u):
    """Return boolean if HTTP/HTTPS resource is compressed"""
    # NOTE: At present (2021-06-15), the only encoding seen is 'gzip' type, but that may change
    return headers(u).get('content-encoding') == 'gzip'


def status(u):
    """Status code of an HTTP/HTTPS resource"""
    result = None
    _cmd = ['/usr/bin/curl', '-I', '-L', '--silent', '-o', '/dev/null', '-w', '"%{http_code}"', '--user-agent', USER_AGENT, u]
    _p = subprocess.run(_cmd, capture_output=True, encoding='utf-8')

    result = int(_p.stdout.strip().replace('"', ''))

    LOG.debug('{cmd} ({http_status}) [exit code {returncode}]'.format(cmd=' '.join(_cmd),
                                                                      http_status=result,
                                                                      returncode=_p.returncode))

    return result


def get(u, dest, quiet=False, resume=False, http2=False, insecure=False, dry_run=False):
    """Fetch HTTP/HTTPS resource to local destination, return a file path object as the result"""
    result = None

    # Convert from path object if destination is not a string
    if isinstance(dest, (Path, PurePath)):
        dest = str(dest)

    # Build the command
    _cmd = ['/usr/bin/curl', '-L', '--user-agent', USER_AGENT, u, '--create-dirs', '-o', dest]

    if quiet:
        _cmd.append('--silent')
    else:
        _cmd.append('--progress-bar')

    # NOTE: Resume really only works for packages and may not actually work as expected
    # if the server doesn't support resume.
    # For example, the Apple audiocontent servers don't seem to properly support resume
    # for the plist files they host, but do for the package files.
    if resume and '.pkg' in u:
        _cmd.append('-C')
        _cmd.append('-')

    # Check for compression on the fly and add in the relevant flag to handle it
    if is_compressed(u):
        LOG.debug('Compressed resource found, updating cURL command')
        _cmd.append('--compressed')

    # HTTP2
    if http2:
        _cmd.append('--http2')
    else:
        _cmd.append('--http1.1')

    # Insecure TLS - not recommended
    if insecure:
        _cmd.append('--insecure')

    if not dry_run:
        # Even though assigned, the progress bar will still output to stdout.
        _p = subprocess.run(_cmd)

    # Log curl command before reverting dest to path object
    LOG.debug('{cmd} [exit code {returncode}]'.format(cmd=' '.join(_cmd), returncode=_p.returncode))

    # Reconvert the destination to a path object
    dest = Path(dest)

    if dest.exists():
        result = dest

    return result
