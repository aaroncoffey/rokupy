"""Toy project to control my roku boxes when the remote has gone missing,
and the official phone app is out of reach.

Docs: https://sdkdocs.roku.com/display/sdkdoc/External+Control+API
"""
# pylint: disable=invalid-name,import-error,missing-docstring,fixme

# TODO: ssdp device discovery, conf file

import sys
from collections import deque
from urllib.request import pathname2url as urlencode

import hammock
import requests.exceptions
import xmltodict

devices = {
    'family_room': 'http://<roku IP>:8060',
    'bedroom': 'http://<another roku ip>:8060'
}

# These device ids can be found with the device-info command, assuming the app is already installed.
apps = {
    'blippi': '72894',
    'netflix': '12',
    'youtube': '837',
    'primevideo': '13',
    'googleplay': '50025',
    'sling': '46041',
    'reuters': '114091'
}

directives = {
    'home': 'home',
    'play': 'play',
    'pause': 'play',
    'fwd': 'fwd',
    'rev': 'rev',
    'select': 'select',
    'left': 'left',
    'right': 'right',
    'up': 'up',
    'down': 'down',
    'back': 'back',
    'info': 'info',
    'backspace': 'backspace',
    'enter': 'enter',
    'instantreplay': 'instantreplay'
}

commands = ['device-info', 'write']

all_commands = commands + [k for k in apps] + [k for k in directives]
if len(all_commands) != len(set(all_commands)):
    print('There must NOT be overlap between commands, please remove the overlapping command and try again.')
    sys.exit(1)

help_msg = (
    '\n'
    'Usage: {script_name} <device> <command>\n'
    'Devices: {devices}\n'
    'Commands: \n'
    '  Apps: {apps}\n'
    '  Controls: {directives}\n'
    '  General: {commands}\n'
    '\n'
    'NOTE: the write command accepts all further arguments as text to be written out to the roku. Example: '
    '"{script_name} <device> write example text" will spell out "example text".\n'
    .format(
        script_name=sys.argv[0],
        devices=', '.join(devices.keys()),
        apps=', '.join(sorted(apps.keys())),
        directives=', '.join(directives.keys()),
        commands=', '.join(sorted(commands))
    )
)


def device_info(roku):
    print('Device Info:')
    dev_info_resp = xmltodict.parse(roku.query('device-info').GET().text)['device-info']
    for k, v in dev_info_resp.items():
        print('    {0}: {1}'.format(k, v))
    print()

    print('Apps:')
    apps_resp = xmltodict.parse(roku.query('apps').GET().text)['apps']['app']
    for app in apps_resp:
        print('    {0}'.format(app['#text']))
        for k, v in app.items():
            print('        {0}: {1}'.format(k, v))
    print()

    print('Active App:')
    active_app_resp = xmltodict.parse(roku.query('active-app').GET().text)['active-app']
    print('    App: {0}'.format(active_app_resp['app']))
    if active_app_resp.get('screensaver'):
        print('    Screensaver:')
        for k, v in active_app_resp['screensaver'].items():
            print('        {0}: {1}'.format(k, v))


def write_string(roku, string):
    errors = 0
    max_errors = 10

    letters = deque([letter for letter in string])
    while letters:
        if errors > max_errors:
            print('Too many errors. Quitting.')
            sys.exit(1)

        curr_letter = letters.popleft()
        print('Sending: {0}'.format(curr_letter))
        resp = roku.keypress('Lit_{0}'.format(urlencode(curr_letter))).POST()
        if not resp.ok:
            errors += 1
            print('Failed to send: {0}'.format(curr_letter))
            letters.appendleft(curr_letter)

    print('👍')


def launch_app(roku, app_id):
    try:
        resp = roku.launch(app_id).POST()
        resp.raise_for_status()
        print('👍')
        return
    except requests.exceptions.HTTPError:
        print('App may not be installed, launching installer on-screen.')

    try:
        resp = roku.install(app_id).POST()
        resp.raise_for_status()
        print('Please follow directions on-screen to install. Quitting.')
        sys.exit(0)
    except requests.exceptions.ConnectionError:
        print('Caught an installer bug, you may need to restart your roku..')
        sys.exit(1)


def main():
    if (
            (len(sys.argv) < 3 or (len(sys.argv) > 3 and sys.argv[2] != 'write')) or
            sys.argv[1] not in devices or
            sys.argv[2] not in all_commands):
        print(help_msg)
        sys.exit(1)

    device = sys.argv[1]
    command = sys.argv[2]
    roku = hammock.Hammock(devices[device])

    if command == 'device-info':
        device_info(roku)
        sys.exit()

    if command in directives:
        resp = roku.keypress(command).POST()
        resp.raise_for_status()
        print('👍')
        sys.exit()

    if command in apps:
        launch_app(roku, apps[command])
        sys.exit()

    if command == 'write':
        string = ' '.join(sys.argv[3:])
        if len(string) > 256:
            print('No need to DOS the roku..')
            sys.exit(1)
        write_string(roku, string)
        sys.exit()


if __name__ == '__main__':
    main()
