#!/usr/bin/env python

import argparse
import sys
import json
import time
import subprocess

import requests
import xmltodict
import zeroconf

'''
See: https://mopria.org/MopriaeSCLSpecDownload.php
'''


def resolve_scanner():
    class ZCListener:
        def __init__(self):
            self.info = None

        def update_service(self, zeroconf, type, name):
            pass

        def remove_service(self, zeroconf, type, name):
            pass

        def add_service(self, zeroconf, type, name):
            self.info = zeroconf.get_service_info(type, name)
    with zeroconf.Zeroconf() as zc:
        listener = ZCListener()
        zeroconf.ServiceBrowser(
            zc, "_uscan._tcp.local.", listener=listener)
        try:
            for i in range(0, 10 * 10):
                if listener.info:
                    break
                time.sleep(.1)
        except:
            pass
    return listener.info


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--source', '-S',
        choices=['feeder', 'flatbed', 'automatic'], default='automatic')
    parser.add_argument(
        '--format', '-f', choices=['pdf', 'jpeg'], default='pdf')
    parser.add_argument('--grayscale', '-g', action='store_true')
    parser.add_argument(
        '--resolution', '-r', type=int, default=200,
        choices=[75, 100, 200, 300, 600])
    parser.add_argument('--debug', '-d', action='store_true')
    parser.add_argument('--no-open', '-o', action='store_false', dest='open')
    parser.add_argument('--quiet', '-q', action='store_true')
    parser.add_argument('--duplex', '-D', action='store_true')
    parser.add_argument('filename')

    args = parser.parse_args()

    info = resolve_scanner()
    if not info:
        print('No scanner found')
        sys.exit(1)
    props = info.properties
    if not args.quiet:
        print(f'Using {info.name}')
    if args.duplex and props[b'duplex'] != b'T':
        print('Duplex not supported', file=sys.stderr)
        sys.exit(1)

    session = requests.Session()

    if args.debug:
        print(info, file=sys.stderr)

    rs = props[b'rs'].decode()
    if rs[0] != '/':
        rs = '/' + rs
    BASE = f'http://{info.server}:{info.port}{rs}'
    if args.debug:
        print(BASE, file=sys.stderr)

    def get_status(job_uuid=None):
        resp = session.get(f'{BASE}/ScannerStatus')
        resp.raise_for_status()
        status = xmltodict.parse(
            resp.text, force_list=('scan:JobInfo'))['scan:ScannerStatus']
        if job_uuid is None:
            return status, None

        uuid_prefix = "urn:uuid:" # Seen in a Brother MFC device
        for jobinfo in status['scan:Jobs']['scan:JobInfo']:
            current_uuid = jobinfo['pwg:JobUuid']
            if current_uuid.startswith(uuid_prefix):
                current_uuid = current_uuid[len(uuid_prefix):]

            if current_uuid == job_uuid:
                return status, jobinfo
        raise RuntimeError('Job not found')

    resp = session.get(f'{BASE}/ScannerCapabilities')
    resp.raise_for_status()
    if args.debug:
        print(resp.text, file=sys.stderr)

    status, _ = get_status()
    if status['pwg:State'] != 'Idle':
        print('Scanner is not idle', file=sys.stderr)
        return 1

    source = {
        'automatic': '',
        'feeder': '<pwg:InputSource>Feeder</pwg:InputSource>',
        'flatbed': '<pwg:InputSource>Flatbed</pwg:InputSource>',
    }[args.source]
    format = {
        'pdf': 'application/pdf',
        'jpeg': 'image/jpeg',
    }[args.format]

    if args.grayscale:
        color = 'Grayscale8'
    else:
        color = 'RGB24'

    job = f'''
    <?xml version="1.0" encoding="UTF-8"?>
    <scan:ScanSettings xmlns:scan="http://schemas.hp.com/imaging/escl/2011/05/03"
      xmlns:pwg="http://www.pwg.org/schemas/2010/12/sm">
      <pwg:Version>2.0</pwg:Version>
      <scan:Intent>TextAndGraphic</scan:Intent>
      <pwg:DocumentFormat>{format}</pwg:DocumentFormat>
      {source}
      <scan:ColorMode>{color}</scan:ColorMode>
      <scan:Duplex>{str(args.duplex).lower()}</scan:Duplex>
      <scan:XResolution>{args.resolution}</scan:XResolution>
      <scan:YResolution>{args.resolution}</scan:YResolution>
    </scan:ScanSettings>
    '''
    resp = session.post(f'{BASE}/ScanJobs', data=job)
    resp.raise_for_status()

    job_uri = resp.headers['location']
    job_uuid = job_uri.split('/')[-1]
    page = 1
    while True:
        status, jobinfo = get_status(job_uuid=job_uuid)
        if args.debug:
            print(json.dumps(jobinfo, indent=2), file=sys.stderr)

        resp = session.get(f'{job_uri}/NextDocument')
        if resp.status_code == 404:
            # We are done
            break
        resp.raise_for_status()

        if args.format == 'pdf':
            with open(args.filename, 'wb') as f:
                f.write(resp.content)
        else:
            with open(f'{args.filename.split(".")[:-1]}-{page}.jpg', 'wb') as f:
                f.write(resp.content)
            page += 1
        if status['pwg:State'] != 'Processing':
            break
        time.sleep(1)

    status, jobinfo = get_status(job_uuid=job_uuid)
    job_reason = jobinfo['pwg:JobStateReasons']['pwg:JobStateReason']
    if args.debug:
        print(job_reason, file=sys.stderr)
    if job_reason != 'JobCompletedSuccessfully':
        return 1

    if args.open:
        if args.format == 'pdf':
            subprocess.run(['open', args.filename])
        else:
            subprocess.run(['open', f'{args.filename.split(".")[:-1]}-1.jpg'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
