import logging
import re

from datetime import datetime

from . import curl
from . import osinfo
from . import plist
from . import APPLICATIONS
from . import FEED_URL
from . import HTTP_OK
from . import SYSTEM_UPDATER
from . import USER_UPDATER

LOG = logging.getLogger(__name__)


def check(apps, latest, check_limit=11):
    """Checks for updates of latest plists on Apple content server and returns the resulting files as a dict"""
    reg = re.compile(r'\d+.plist')  # Compiled regex to strip the version value and plist file extension
    apps = sorted([re.sub(reg, '', app) for app in apps])  # Have to convert these over to basic app names not plist values
    supported = [_k for _k, _ in APPLICATIONS.items()]
    result = latest if latest else dict()  # Used if the file doesn't exist or has no updated apps
    found_updates = {'garageband': None,
                     'logicpro': None,
                     'mainstage': None}

    # Source the correct plist to read preferences
    if osinfo.isroot():
        updater_pref = SYSTEM_UPDATER
    else:
        updater_pref = USER_UPDATER

    # Read the last update done to iterate over, ensuring the most recent files that were ok are sourced
    last_update = plist.read(f=updater_pref) if updater_pref.exists() else None

    # If the last update doesn't exist, fetch it
    if not last_update:
        plist.write(d=result, f=updater_pref)
        last_update = result.copy()

    # Iterate over the apps in the last update and get the version value from the plist filename
    # and then jump forward N number of versions to check.
    check_msg = ['Checking for updated sources to {apps}'.format(apps=', '.join(apps))]

    if last_update.get('last_checked'):
        date = last_update['last_checked'].strftime('%Y-%m-%d %H:%M:%S')
        check_msg.append(' (last checked {date})'.format(date=date))

    # Print check message and last check time
    LOG.info(''.join(check_msg))

    for app, source_plist in last_update.items():
        if app in (supported and apps):
            ver = int(source_plist.replace(app, ''))

            # Create a URL to check, make sure it exists, if it does, update the result dict.
            # This should always return the current 'latest' version if no URL's are found
            for new_ver in range(ver, ver + check_limit):
                new_plist = '{app}{ver}'.format(app=app, ver=new_ver)
                url = '{feedurl}/{plist}.plist'.format(feedurl=FEED_URL, plist=new_plist)

                LOG.debug('Checking {url}'.format(url=url))

                status = curl.status(url)

                if status in HTTP_OK and new_plist != result[app]:
                    found_updates[app] = new_plist
                    result[app] = new_plist
                    result['last_updated'] = datetime.now()  # Include a timestamp for the last with successfull update.
                    LOG.debug('Found updated source plist at {url}'.format(url=url))

    # Include a last checked timestamp
    result['last_checked'] = datetime.now()

    # Write the results
    if result:
        plist.write(d=result, f=updater_pref)

    # Collect the updated apps and generate a list of strings to use in update found message.
    updated_apps = ['{plist}.plist'.format(plist=new_plist) for app, new_plist in found_updates.items() if new_plist]

    # Log the updates found
    if updated_apps:
        LOG.info('Found updated sources {updates}, using updated sources'.format(updates=', '.join(updated_apps)))
    else:
        LOG.info('No updated sources found for {apps}, using last known current sources'.format(apps=', '.join(apps)))

    result = {_k: _v for _k, _v in result.items() if _k in apps}

    return result
