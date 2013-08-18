"""
putio.py is an api wrapper for put.io


Example usage:

>>> client = putio.Client(OAUTH_TOKEN)

test if token is valid:
>>> client.check_token()

list files:
>>> client.File.list()

add a new transfer:
>>> new = client.Transfer.add_url('http://example.com/good.torrent')

download file as zip:
>>> client.File.download_zip(new['file_id'], dest='/tmp/')

"""

import os
import re
import json
import logging
import requests
import datetime
from time import sleep

BASE_URL = 'https://api.put.io/v2'

logger = logging.getLogger(__name__)


class Client(object):
    """
    Creates a session to put.io with your access token.

    Variables:
        File
            Gives access to file actions
        Transfer
            Gives access to transfer actions
    """
    def __init__(self, access_token):
        self.access_token = access_token
        self.session = requests.session()

        self.File = _File(self)  # Contain file actions
        self.Transfer = _Transfer(self)  # Contain transfer actions

    def check_token(self):
        """Returns True if token is valid, False otherwise"""
        r = self.request('/account/info')
        return 'status' in r and r['status'] == 'OK'

    def request(self, path, method='GET', params=None, data=None, files=None,
                headers=None, raw=False):
        """
        Wrapper around requests.request()

        Prepends BASE_URL to path.
        Inserts oauth_token to query params.
        Parses response as JSON and returns it.

        """
        if not params:
            params = {}

        if not headers:
            headers = {}

        # All requests must include oauth_token
        params['oauth_token'] = self.access_token

        headers['Accept'] = 'application/json'

        url = BASE_URL + path
        logger.debug('url: %s', url)

        #Try 3 times:
        for i in range(1, 4):
            try:
                response = self.session.request(
                    method, url, params=params, data=data, files=files,
                    headers=headers, allow_redirects=True, stream=raw)
                logger.debug('response: %s', response)
                break
            except requests.exceptions.ConnectionError as e:
                logger.debug(e)
                logger.warning('A Connection error occurred (%s/3)' % i)
                response = None
                if i != 3:  # Don't sleep the last time
                    sleep(5*i)

    #On failed response:
        if response is None:
            logger.error('Failed to connect %s times, giving up' % i)
            if raw:
                return
            else:
                return {'status': 'ERROR',
                        'error_type': 'A Connection error occurred',
                        'error_message': 'Failed to connect %s times, giving up' % i}

    #On success response:
        if raw:
            return response

        logger.debug('content: %s', response.content)
        try:
            response = json.loads(response.content)
        except ValueError:
            logger.error('Received invalid JSON from put.io')
            response = {'status': 'ERROR',
                        'error_type': 'JSON ValueError',
                        'error_message': 'Received invalid JSON from put.io'}

        return response


class _File(object):
    """A class for file operations"""
    def __init__(self, parent):
        self.client = parent

    def get(self, id):
        """Returns a file's properties"""
        d = self.client.request('/files/%i' % id)
        if d['status'] == 'ERROR':
            return {}
        return d['file']

    def list(self, parent_id=0):
        """Lists files in a folder"""
        d = self.client.request('/files/list', params={'parent_id': parent_id})
        if d['status'] == 'ERROR':
            return {}
        return d['files']

    def upload(self, path, name=None):
        """Uploads a file. If the uploaded file is a torrent file, starts it as a transfer"""
        with open(path) as f:
            if name:
                files = {'file': (name, f)}
            else:
                files = {'file': f}
            d = self.client.request('/files/upload', method='POST', files=files)
        if d['status'] == 'ERROR':
            return {}
        return d['file']

    #TODO: rewrite this function ...... !!
    def download(self, file_id, dest='.', zip=False):
        """Download the contents of the file

        Returns the filename on success, or False otherwise.
        """
        if not zip:
            response = self.client.request('/files/%s/download' % file_id, raw=True)
        else:
            response = self.client.request('/files/zip', params={'file_ids': str(file_id)}, raw=True)

        if not response.ok:
            logger.info('Failed to download file with id: %s', file_id)
            return

        filename = re.match(
            'attachment; filename=(?:"(.*)"|(.*))',
            response.headers['Content-Disposition'])
        filename = filename.groups()[0] or filename.groups()[1]
        total_length = response.headers.get('Content-Length')

        with open(os.path.join(dest, filename), 'wb') as f:
            current_time = datetime.datetime.now()
            if total_length is None:
                f.write(response.content)  # No error checkking can be done, just dump data
            else:
                total_length = int(total_length)
                logger.info('Total size of file: %s MB' % (total_length / 1024 / 1024))
                self._write_data_with_progress(f, response, total_length)

                #If we did not receive everything, try to download missing chunks.
                attempts = 1
                MAX_ATTEMPTS = 10
                while f.tell() != total_length:
                    logger.warning('Download failed (%s/%s), will try to resume. Got %s of %s bytes (%s %%)'
                                   % (attempts, MAX_ATTEMPTS, f.tell(), total_length, int(f.tell() * 100 / total_length)))
                    headers = {'range': 'bytes=%s-' % (f.tell())}  # Get rest of file
                    if not zip:
                        response = self.client.request('/files/%s/download' % file_id, raw=True, headers=headers)
                    else:
                        response = self.client.request('/files/zip', params={'file_ids': str(file_id)}, raw=True, headers=headers)

                    if not response or response.headers.get('Content-Length') is None:
                        logger.error('Failed to resume download')
                        return

                    partial_length = int(response.headers.get('Content-Length'))
                    logger.info('Getting partial file with size: %s MB' % (partial_length / 1024 / 1024))
                    self._write_data_with_progress(f, response, partial_length)

                    if attempts == MAX_ATTEMPTS:
                    #If we still did not get the whole file, give up.
                        logger.error('Failed to download rest of file after %s tries. Got %s of %s bytes' % (attempts, f.tell(), total_length))
                        return
                    attempts += 1

                download_time = datetime.datetime.now() - current_time
                download_speed = int(f.tell() / download_time.total_seconds() / 1024)  # in KB/s
                logger.info('Download time: %s, avg speed: %s KB/s' % (download_time, download_speed))
        return filename

    def download_zip(self, file_id, dest='.'):
        """Downloads the contents of the file as a zip archive

        Returns the filename on success, or False otherwise.
        """
        return self.download(file_id, dest, zip=True)

    def delete(self, file_id):
        """Deletes given files"""
        d = self.client.request('/files/delete', method='POST', data={'file_ids': str(file_id)})
        if d['status'] == 'ERROR':
            return {}
        return d

    def create_folder(self, name, parent_id=''):
        """Creates a new folder."""
        d = self.client.request('/files/create-folder', method='POST', data={'name': str(name), 'parent_id': str(parent_id)})
        if d['status'] == 'ERROR':
            return {}
        return d['file']

    @staticmethod
    def _write_data_with_progress(file, source, length):
        dl = 0
        chunk = length / 100 or 1
        for data in source.iter_content(chunk):
            dl += chunk
            file.write(data)
            logger.info('Download progress: %s%%' % (100 * dl / length))


class _Transfer(object):
    """A class for transfer operations"""
    def __init__(self, parent):
        self.client = parent

    def list(self):
        """Lists active transfers. If transfer is completed, it is removed from the list"""
        d = self.client.request('/transfers/list')
        if d['status'] == 'ERROR':
            return {}
        return d['transfers']

    def clean(self):
        """Clean completed transfers from the list."""
        d = self.client.request('/transfers/clean', method='POST')
        if d['status'] == 'ERROR':
            return {}
        return d

    def get(self, id):
        """Returns a transfer's properties"""
        d = self.client.request('/transfers/%i' % id)
        if d['status'] == 'ERROR':
            return {}
        return d['transfer']

    def cancel(self, id):
        """Deletes the given transfers."""
        d = self.client.request('/transfers/cancel', method='POST',
                                data=dict(transfer_ids=id))
        if d['status'] == 'ERROR':
            return {}
        return d['transfer']

    def add_url(self, url, parent_id=0, extract=False, callback_url=None):
        """Adds a new transfer"""
        d = self.client.request('/transfers/add', method='POST', data=dict(
            url=url, parent_id=parent_id, extract=extract,
            callback_url=callback_url))
        if d['status'] == 'ERROR':
            return {}
        return d['transfer']

    def add_torrent(self, path, parent_id=0, extract=False, callback_url=None):
        """Adds a new torrent transfer"""
        with open(path) as f:
            files = {'file': f}
            d = self.client.request('/files/upload', method='POST', files=files,
                                    data=dict(parent_id=parent_id,
                                              extract=extract,
                                              callback_url=callback_url))
        if d['status'] == 'ERROR':
            return {}
        return d['transfer']
