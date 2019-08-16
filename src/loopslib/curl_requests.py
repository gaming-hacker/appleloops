"""Contains the class for using CURL."""
import logging
import re
import subprocess

try:
    import config
    import curl_errors
except ImportError:
    from . import config
    from . import curl_errors

LOG = logging.getLogger(__name__)


class CURL(object):
    """Class for using CURL."""
    def __init__(self, url=None, silent_override=False):
        self._url = url
        self._silent_override = silent_override
        self._curl_path = '/usr/bin/curl'

        self.headers = None
        self.status = None
        self.curl_error = None

        if self._url:
            self.headers = self._get_headers(obj=self._url)
            self.status = self._get_status()

    def _get_headers(self, obj):
        """Gets the headers of the provided URL, and returns the result as a dictionary.
        Does not follow redirects."""
        result = None
        redirect_statuses = ['301 Moved Permanently',
                             '302 Found',
                             '302 Moved Temporarily',
                             '303 See Other',
                             '307 Temporary Redirect',
                             '308 Permanent Redirect']

        cmd = [self._curl_path,
               '--user-agent',
               config.USERAGENT,
               '--silent',  # Getting headers/status should always be silent.
               '-I',
               '-L',
               obj]

        if config.PROXY:
            cmd.extend(['--proxy', config.PROXY])

        if config.ALLOW_INSECURE_CURL:
            cmd.extend(['--insecure'])

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p_result, p_error = process.communicate()

        # pylint: disable=too-many-nested-blocks
        if process.returncode is 0:
            if isinstance(p_result, bytes):
                result = dict()
                # There's a trailing `\n` in the output, so tidy it up.
                p_result = p_result.decode().strip()

                # This handles if there is a redirect
                if '\r\n\r' in p_result and any([status.lower() in p_result.lower() for status in redirect_statuses]):
                    p_result = p_result.split('\r\n\r')
                    p_result = p_result[-1]  # The redirect should be the last item in the output.

                # Now tidy up
                p_result = p_result.strip().splitlines()

                for line in p_result:
                    if re.match(r'^HTTP/\d{1}.\d{1} ', line) and ':' not in line:
                        result['Status'] = line

                        # Set the status code as a seperate value so we can minimise curl usage.
                    else:
                        if ':' in line:
                            key = line.split(': ')[0]
                            value = ''.join(line.split(': ')[1:])

                            if 'content-length' in key.lower():
                                value = int(value)

                            result[key] = value
                LOG.debug('{}: {}'.format(' '.join(cmd), result))
        elif process.returncode in curl_errors.CURL_ERRORS.keys():
            _err_msg = curl_errors.CURL_ERRORS.get(process.returncode, None)

            # Set the 'self.curl_error' attribute to the error received.
            self.curl_error = {'cURL_Error': process.returncode,
                               'Error_Msg': _err_msg}

            LOG.debug('{}: {} - {}'.format(' '.join(cmd),
                                           self.curl_error.get('cURL_Error'),
                                           self.curl_error.get('Error_Msg')))
        else:
            LOG.debug('{}: {}'.format(' '.join(cmd), p_error))
            # May need to not print the error out in certain circumstances
            print('Error:\n{}'.format(p_error))
        # pylint: enable=too-many-nested-blocks

        return result

    def _get_status(self):
        """Returns the HTTP status code as its own attribute."""
        result = None

        if self.headers:
            status = self.headers.get('Status', None)

            # HTTP status codes should be the first three numbers of this header.
            if status:
                result = re.sub(r'^HTTP/\d{1}.\d{1} ', '', status).split(' ')[0]

        if result:
            try:
                result = int(result)
            except Exception:
                raise

        return result

    def get(self, url, output=None):
        """Retrieves the specified URL. Saves it to path specified in 'output' if present."""
        # NOTE: Must ignore 'dry run' state for any '.plist' file downloads.
        _fetching_plist = url.endswith('.plist')

        # Now the command.
        cmd = [self._curl_path,
               '--user-agent',
               config.USERAGENT,
               '-L',
               '-C',
               '-',
               url]

        if config.PROXY:
            cmd.extend(['--proxy', config.PROXY])

        if config.ALLOW_INSECURE_CURL:
            cmd.extend(['--insecure'])

        if not (config.QUIET or config.SILENT or self._silent_override or _fetching_plist):
            cmd.extend(['--progress-bar'])
        elif (config.QUIET or config.SILENT or self._silent_override or _fetching_plist):
            cmd.extend(['--silent'])

        if output:
            cmd.extend(['--create-dirs', '-o', output])

        LOG.debug('CURL get: {}'.format(' '.join(cmd)))

        if not config.DRY_RUN or _fetching_plist:
            try:
                LOG.info('Downloading {}'.format(url))

                if not (config.QUIET or config.SILENT or self._silent_override or _fetching_plist):
                    print('Downloading {}'.format(url))

                subprocess.check_call(cmd)
            except subprocess.CalledProcessError as e:
                LOG.debug('{}: {}'.format(' '.join(cmd), e))
                raise e
        elif config.DRY_RUN:
            if not config.SILENT:
                _msg = 'Download {}'.format(url)

                print(_msg)
                LOG.info(_msg)
