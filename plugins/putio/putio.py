from flask import render_template, Blueprint, request, redirect, flash
from plugins.settings import register_setting
from putio_ext.putio import Client
from plugins.db import db_get_settings, db_set_settings

import paho.mqtt.publish as publish
import os
import sys
import subprocess
import fileinput
import re

blueprint = Blueprint('putio', __name__, url_prefix='/putio', template_folder='templates', static_folder='static')


_leftbar = []
_leftbar.append({'href': '/putio', 'caption': 'Generic'})
_leftbar.append({'href': '/putio/episode', 'caption': 'Episode'})
_leftbar.append({'href': '/putio/info', 'caption': 'Put.io info'})
_leftbar.append({'href': '/putio/queue', 'caption': 'Queue'})
_leftbar.append({'href': '#', 'caption': '------'})
_leftbar.append({'href': '/putio/runscript', 'caption': 'Run script'})

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
        mqtt = request.form.get('mqtt', False)
        redirect_to_log = request.form.get('redirect_to_log', False)

        is_episode = False

        settings = db_get_settings('putio')
        if not 'log_file' in settings:
            output = None
        output = open(settings['log_file'], 'a')

        if url and showname and season and episode:
            is_episode = True
            args = [_script, url, '--showname', showname, '--season', season, '--episode', episode]

            if mqtt:
                args.append('--mqtt')

            subprocess.Popen(args, stdout=output, stderr=output, close_fds=True)
        elif url:
            if button == 'Generic':
                args = [_script, url]

                if mqtt:
                    args.append('--mqtt')

                subprocess.Popen(args, stdout=output, stderr=output, close_fds=True)
            elif button == 'Music':
                args = [_script, url, '--music']

                if mqtt:
                    args.append('--mqtt')

                subprocess.Popen(args, stdout=output, stderr=output, close_fds=True)
            else: # Movie
                title = title if title else 'auto'
                args = [_script, url, '--moviename', title]

                if mqtt:
                    args.append('--mqtt')

                subprocess.Popen(args, stdout=output, stderr=output, close_fds=True)
        else:
            flash('Failed to start download')
            output.close()
            return render_template('putio_generic.html')

        output.close()
        if redirect_to_log:
            return redirect('/logs/putio.log')

        if is_episode:
            return redirect('/putio/episode')
        return redirect('/putio')
    else:  # GET
        return render_template('putio_generic.html', queue=_get_pickles(), pidfile=_pidfile_exist())


@blueprint.route('/episode')
def episodeview():
    return render_template('putio_episode.html')

@blueprint.route('/info')
def info():
    return render_template('putio_putio.html', queue=_get_pickles(), pidfile=_pidfile_exist(), transfers=_get_transfers(), files=_get_files())

@blueprint.route('/queue/<pickle>', methods=['GET', 'POST'])
@blueprint.route('/queue')
def queue(pickle = False):
    if request.method == 'POST' and pickle:
        settings = db_get_settings('putio')

        newName = request.form.get('newName', '')

        if pickle and newName != pickle and 'work_dir' in settings:
            ret = os.rename(os.path.join(settings['work_dir'], pickle), os.path.join(settings['work_dir'], newName))
            if ret:
                flash('Renamed pickle to: ' + newName)
            else:
                flash('Failed to rename pickle')
            pickle = False
        else:
            flash('Weirdness')
    return render_template('putio_queue.html', queue=_get_pickles(), pickle=pickle)


@blueprint.route('/runscript')
def runscript():
    settings = db_get_settings('putio')
    if not 'log_file' in settings:
        output = None
    output = open(settings['log_file'], 'a')
    subprocess.Popen([_script], stdout=output, stderr=output, close_fds=True)

    return redirect('/putio')


@blueprint.route('/clean/transfers')
def clean():
    settings = db_get_settings('putio')
    if 'token' in settings:
        client = Client(settings['token'])
        client.Transfer.clean()
    return redirect('/putio')


@blueprint.route('/delete/download/<file_id>')
def delete_dlownload(file_id):
    settings = db_get_settings('putio')
    if not 'token' in settings:
        return redirect('/putio')
    client = Client(settings['token'])
    response = client.File.delete(file_id)
    if response:
        flash('Deleted put.io download with id: ' + file_id)
    return redirect('/putio')


@blueprint.route('/delete/pickle/<pickle>')
def delete_pickle(pickle):
    settings = db_get_settings('putio')
    if not 'work_dir' in settings:
        flash('Delete failed: No work_dir in settings')
        return redirect('/putio')

    if not pickle.endswith('.putio.pickle'):
        flash('Delete failed: Not a putio pickle file')
        return redirect('/putio')

    pickle_file = os.path.join(settings['work_dir'], pickle)

    if not os.path.isfile(pickle_file):
        flash('Delete failed: Not a valid file')
        return redirect('/putio')

    try:
        os.unlink(pickle_file)
    except Exception:
        flash('Delete failed: unlink failed')
        return redirect('/putio')
    else:
        flash('Deleted pickle file: ' + pickle)
        return redirect('/putio')


@blueprint.route('/delete/pidfile')
def rmpidfile():
    settings = db_get_settings('putio')
    if not 'work_dir' in settings:
        return False

    pidfile = os.path.join(settings['work_dir'], 'putio_flexget.pid')

    if not os.path.isfile(pidfile):
        flash('Delete failed: pidfile does not exist')
    try:
        os.unlink(pidfile)
    except Exception:
        flash('Delete failed: failed to delete: '+ pidfile)
    else:
        flash('Deleted pidfile: ' + pidfile)

    return redirect('/putio')


def _get_transfers():
    settings = db_get_settings('putio')
    if not 'token' in settings:
        return
    client = Client(settings['token'])
    return client.Transfer.list()


def _get_files():
    settings = db_get_settings('putio')
    if not 'token' in settings:
        return
    client = Client(settings['token'])
    return client.File.list()


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


def _pidfile_exist():
    settings = db_get_settings('putio')
    if not 'work_dir' in settings:
        return False

    return os.path.isfile(os.path.join(settings['work_dir'], 'putio_flexget.pid'))



def settings():
    if request.method == 'POST':
        token = request.form.get('token', '')
        mqtt_server = request.form.get('mqtt_server', '')
        work_dir = request.form.get('work_dir', '')
        show_dir = request.form.get('show_dir', '')
        movie_dir = request.form.get('movie_dir', '')
        generic_dir = request.form.get('generic_dir', '')
        music_dir = request.form.get('music_dir', '')
        log_file = request.form.get('log_file', '')

        #Nasty !!!!
        #CHANGING VARIABLES IN SCRIPT FILE
        #Should use db instead, but would brake the way the script is called from flexget !?
        last = False
        for line in fileinput.input(_script, inplace=True):
            if not last:
                if 'TOKEN =' in line:
                    line = re.sub(r"'.*'$", "'%s'" % token, line)
                elif 'MQTT_SERVER =' in line:
                    line = re.sub(r"'.*'$", "'%s'" % mqtt_server, line)
                elif 'WORK_DIR =' in line:
                    line = re.sub(r"'.*'$", "'%s'" % work_dir, line)
                elif 'SHOW_DIR =' in line:
                    line = re.sub(r"'.*'$", "'%s'" % show_dir, line)
                elif 'MOVIE_DIR =' in line:
                    line = re.sub(r"'.*'$", "'%s'" % movie_dir, line)
                elif 'GENERIC_DIR =' in line:
                    line = re.sub(r"'.*'$", "'%s'" % generic_dir, line)
                elif 'MUSIC_DIR =' in line:
                    line = re.sub(r"'.*'$", "'%s'" % music_dir, line)
                elif 'LOG_FILE =' in line:
                    last = True
                    line = re.sub(r"'.*'$", "'%s'" % log_file, line)
            sys.stdout.write(line)
        fileinput.close()

        flash('Put.io settings updated!')

        settings = dict(token=token,
                        mqtt_server=mqtt_server,
                        work_dir=work_dir,
                        show_dir=show_dir,
                        movie_dir=movie_dir,
                        generic_dir=generic_dir,
                        music_dir=music_dir,
                        log_file=log_file
                        )
        db_set_settings('putio', settings, clean=True)
    else:  # GET
        settings = db_get_settings('putio')
        if request.args.get('mqtt_test') and mqtt_server in settings:
            publish.single('myflexget/test', 'Test MQTT from MyFlexget', hostname=settings['mqtt_server'])

    return render_template('putio_settings.html', settings=settings)


def register_plugin():
    return blueprint, 'Put.io'


register_setting('putio', 'Put.io', settings)
