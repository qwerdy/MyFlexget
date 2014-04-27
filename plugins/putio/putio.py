from flask import render_template, Blueprint, request, redirect, flash
from plugins.settings import register_setting
from putio_ext.putio import Client
from plugins.db import db_get_settings, db_set_settings

import os
import sys
import subprocess
import fileinput
import re

blueprint = Blueprint('putio', __name__, url_prefix='/putio', template_folder='templates', static_folder='static')


_leftbar = []
_leftbar.append({'href': '/putio', 'caption': 'Generic'})
_leftbar.append({'href': '/putio/episode', 'caption': 'Episode'})
_leftbar.append({'href': '/putio/clean', 'caption': 'Clean list'})

_script = os.path.dirname(os.path.abspath(__file__))
_script = os.path.join(_script, 'putio_ext', 'putio_download.py')


@blueprint.context_processor
def variables():
    return {'leftbar': _leftbar}


@blueprint.route('', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form.get('url', '')
        title = request.form.get('title', '')
        showname = request.form.get('name', '')
        season = request.form.get('season', '')
        episode = request.form.get('episode', '')
        button = request.form.get('submit', '')

        settings = db_get_settings('putio')
        if not 'log_file' in settings:
            output = None
        output = open(settings['log_file'], 'a')

        if url and showname and season and episode:
            subprocess.Popen([_script, url, showname, season, episode], stdout=output, stderr=output, close_fds=True)
        elif url:
            if button == 'Generic':
                subprocess.Popen([_script, url], stdout=output, stderr=output, close_fds=True)
            else:
                title = title if title else 'auto'
                subprocess.Popen([_script, url, title], stdout=output, stderr=output, close_fds=True)
        else:
            flash('Failed to start download')
            output.close()
            return render_template('putio_generic.html')

        output.close()
        return redirect('/logs/putio.log')
    else:  # GET
        return render_template('putio_generic.html', queue=_get_pickles(), transfers=_get_transfers())


@blueprint.route('/episode')
def episode():
    return render_template('putio_episode.html')


@blueprint.route('/clean')
def clean():
    settings = db_get_settings('putio')
    if 'token' in settings:
        client = Client(settings['token'])
        client.Transfer.clean()
    return redirect('/putio')


def _get_transfers():
    settings = db_get_settings('putio')
    if not 'token' in settings:
        return
    client = Client(settings['token'])
    return client.Transfer.list()


def _get_pickles():
    queue = []
    settings = db_get_settings('putio')
    if not 'work_dir' in settings:
        return queue

    files = os.listdir(settings['work_dir'])
    for f in sorted(files):
        if f.endswith('.putio.pickle'):
            queue.append(f)
    return queue


def settings():
    if request.method == 'POST':
        token = request.form.get('token', '')
        work_dir = request.form.get('work_dir', '')
        show_dir = request.form.get('show_dir', '')
        movie_dir = request.form.get('movie_dir', '')
        generic_dir = request.form.get('generic_dir', '')
        log_file = request.form.get('log_file', '')

        #Nasty !!!!
        #CHANGING VARIABLES IN SCRIPT FILE
        #Should use db instead, but would brake the way the script is called from flexget !?
        last = False
        for line in fileinput.input(_script, inplace=True):
            if not last:
                if 'TOKEN =' in line:
                    line = re.sub(r"'.*'$", "'%s'" % token, line)
                elif 'WORK_DIR =' in line:
                    line = re.sub(r"'.*'$", "'%s'" % work_dir, line)
                elif 'SHOW_DIR =' in line:
                    line = re.sub(r"'.*'$", "'%s'" % show_dir, line)
                elif 'MOVIE_DIR =' in line:
                    line = re.sub(r"'.*'$", "'%s'" % movie_dir, line)
                elif 'GENERIC_DIR =' in line:
                    line = re.sub(r"'.*'$", "'%s'" % generic_dir, line)
                elif 'LOG_FILE =' in line:
                    last = True
                    line = re.sub(r"'.*'$", "'%s'" % log_file, line)
            sys.stdout.write(line)
        fileinput.close()

        flash('Put.io settings updated!')

        settings = dict(token=token,
                        work_dir=work_dir,
                        show_dir=show_dir,
                        movie_dir=movie_dir,
                        generic_dir=generic_dir,
                        log_file=log_file
                        )
        db_set_settings('putio', settings, clean=True)
    else:  # GET
        settings = db_get_settings('putio')
    return render_template('putio_settings.html', settings=settings)


def register_plugin():
    return blueprint, 'Put.io'


register_setting('putio', 'Put.io', settings)
