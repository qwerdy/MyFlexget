from flask import render_template, Blueprint, request, flash
from myflexget import register_plugin, app_folder
from plugins._db import db_get, db_get_settings
from utils.functions import value_in_range
import os


blueprint = Blueprint('settings', __name__, url_prefix='/settings', template_folder='templates')


_leftbar = []
_leftbar.append({'href': '/settings', 'caption': 'Flexget'})
_leftbar.append({'href': '/settings/myepisode', 'caption': 'Myepisode'})
_leftbar.append({'href': '/settings/schedule', 'caption': 'Schedule'})


def check_settings(flexget, path, script):
    error = []

    # Remove flexget pattern from path
    if path.find('{') > 0:
        path = path[0:path.find('{')]

    if not os.access(flexget, os.R_OK):
        error.append('No access to flexget bin path: '+flexget)
    if not os.access(path, os.W_OK):
        error.append('Download Path is not writable: '+path)
    if script and not os.access(script[0:script.find(' ')], os.R_OK):  # stop if match flexget pattern
        error.append('No access to script file: '+script)
    if not os.access(os.path.join(app_folder, 'tmp'), os.W_OK):
        error.append('tmp folder in app-root is not writable')

    return error


@blueprint.context_processor
def variables():
    return {'leftbar': _leftbar}


@blueprint.route('', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        email = request.form.get('email', '')
        rss = request.form.get('rss', '')
        flexget = request.form.get('flexget', '')
        path = request.form.get('path', '')
        dq = request.form.get('dq', '')
        hq = request.form.get('hq', '')
        limit = request.form.get('limit', '')
        p_api = request.form.get('p_api', '')
        script_exec = request.form.get('script_exec', '')

        settings = request.form
        if rss and flexget and path and dq:
            errors = check_settings(flexget, path, script_exec)
            if errors:
                for error in errors:
                    flash(error, 'error')
            else:
                db = db_get()
                db.execute('delete from settings_new where id="flexget"')
                db.execute('''insert into settings_new
                              (key, value, id) values
                              ("email", ?, "flexget"),
                              ("rss", ?, "flexget"),
                              ("flexget", ?, "flexget"),
                              ("path", ?, "flexget"),
                              ("dq", ?, "flexget"),
                              ("hq", ?, "flexget"),
                              ("limit", ?, "flexget"),
                              ("p_api", ?, "flexget"),
                              ("script_exec", ?, "flexget")''',
                           [email, rss, flexget, path, dq, hq, limit, p_api, script_exec])
                db.commit()
                flash('Flexget settings updated!')
                settings = db_get_settings('flexget')
        else:
            flash('ERROR! Missing data!', 'error')
    else:  # GET
        settings = db_get_settings('flexget')

    return render_template('settings_flexget.html', settings=settings)


@blueprint.route('/myepisode', methods=['GET', 'POST'])
def myepisode():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        if username and password:
            db = db_get()
            db.execute('delete from settings_new where id="myepisode"')
            db.execute('''insert into settings_new
                          (key, value, id) values
                          ("username", ?, "myepisode"),
                          ("password", ?, "myepisode")''',
                       [username, password])
            db.commit()
            flash('Myepisode settings updated!')
        else:
            flash('ERROR! Missing data!', 'error')

    settings = db_get_settings('myepisode')
    return render_template('settings_myepisode.html', settings=settings)


@blueprint.route('/schedule', methods=['GET', 'POST'])
def schedule():
    if request.method == 'POST':
        try:
            start = value_in_range(int(request.form.get('start', '')), 0, 23)
            end = value_in_range(int(request.form.get('end', '')), start+1, 23)
            hour = value_in_range(int(request.form.get('hour', '')), 0, 23)
            minute = value_in_range(int(request.form.get('minute', '')), 0, 59)
        except ValueError:
            flash('ERROR! Invalid data!', 'error')
            settings = request.form
        else:
            db = db_get()
            db.execute('delete from settings_new where id="schedule"')
            db.execute('''insert into settings_new
                          (key, value, id) values
                          ("start", ?, "schedule"),
                          ("end", ?, "schedule"),
                          ("hour", ?, "schedule"),
                          ("minute", ?, "schedule")''',
                       [start, end, hour, minute])
            db.commit()
            flash('Schedule settings updated!')
            settings = db_get_settings('schedule')
    else:  # GET
        settings = db_get_settings('schedule')
    return render_template('settings_schedule.html', settings=settings)


register_plugin(blueprint, menu='Settings', order=200)
