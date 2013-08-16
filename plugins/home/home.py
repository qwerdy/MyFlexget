from flask import render_template, redirect, abort, flash, request
from flask import Blueprint
from myflexget import app_folder
from utils.myepisodes import Myepisodes
from utils.flexget import generateyml, flexget
from plugins._db import db_query, db_get_settings
import utils.session as sess

from apscheduler.scheduler import Scheduler
import os


blueprint = Blueprint('index', __name__, url_prefix='/', template_folder='templates')

_leftbar = []
_leftbar.append({'href': '/nextshows', 'caption': 'Next shows'})
_leftbar.append({'href': '/config', 'caption': 'Config'})
_leftbar.append({'href': '/stop', 'caption': 'Stop'})


@blueprint.context_processor
def variables():
    return {'leftbar': _leftbar}


@blueprint.route('/')
def index():
    jobs = []
    if sess.mysched:
        jobs = sess.mysched.get_jobs()
        return render_template('home_home.html', jobs=jobs)
    return render_template('home_home.html', leftbar=[{'href': 'start', 'caption': 'Start'}], offline='')


@blueprint.route('runnow')
def runnow():
    if not sess.mysched:
        abort(403)
    flexget(runnow=True)
    return redirect('')


@blueprint.route('start')
def start():
    if sess.mysched:
        abort(409)

    creds = db_get_settings('myepisode')
    settings = db_get_settings('flexget')
    sched = db_get_settings('schedule')

    username = creds['username'] if 'username' in creds else ''
    password = creds['password'] if 'password' in creds else ''

    sess.myep = Myepisodes(username, password)
    if sess.myep.logged_in():
        if not 'hour' in sched or not 'minute' in sched:
            flash('Missing scheduler settings', 'error')
        elif not settings:
            flash('Missing flexget settings', 'error')
        else:
            sess.mysched = Scheduler()
            sess.mysched.start()
            sess.mysched.add_cron_job(generateyml, hour=sched['hour'], minute=sched['minute'])
            flash('Schedule added!')
    else:
        flash('Myepisodes failed login! Check credentials!', 'error')
    return redirect('')


@blueprint.route('stop')
def stop():
    if not sess.mysched:
        abort(403)

    sess.mysched.shutdown()
    sess.mysched = None
    sess.myep = None
    flash('Schedule stopped!')
    return redirect('')


@blueprint.route('nextshows')
@blueprint.route('nextshows/<day>')
def nextshows(day=''):
    if not sess.mysched or not sess.myep:
        abort(403)

    if day == 'today':
        shows = sess.myep.get_dayShows('today')
    else:
        shows = sess.myep.get_dayShows()  # tomorrow
    ig_shows = [show[0] for show in db_query('select name from shows where ignore="1"')]
    shows = [x for x in shows if x['showname'] not in ig_shows and not x['aquired']]

    return render_template('home_nextshows.html', shows=shows)


@blueprint.route('config', methods=['GET', 'POST'])
def config():
    if not sess.mysched or not sess.myep:
        abort(403)

    config_file = os.path.join(app_folder, 'tmp', 'testconfig.yml')
    if request.method == 'POST':
        content = request.form.get('content', '')
        f = open(config_file, 'w')
        f.write(content)
        f.close()
        flash('Config file updated!')

    if os.path.isfile(config_file):
        f = open(config_file, 'r')
        content = f.read()
        f.close()
    else:
        content = ''

    return render_template('home_config.html', file=content)


@blueprint.route('new/<day>')
def new(day):
    if not sess.mysched or not sess.myep:
        abort(403)

    if day not in ('today', 'tomorrow', 'yesterday'):
        flash('Day is not supported!', 'error')
    else:
        if generateyml(sched=False, day=day):
            flash('Generated yml file for %s' % day)
        else:
            flash('Failed to generated yml file for %s' % day, 'error')

    return redirect('/config')


@blueprint.route('sched/<day>')
def sched(day):
    if not sess.mysched or not sess.myep:
        abort(403)

    if day not in ('today', 'tomorrow'):
        flash('Day is not supported!', 'error')
    else:
        if generateyml(day=day, notify=False):
            flash('Scheduled created for %s' % day)
        else:
            flash('Failed to create schedule for %s' % day, 'error')

    return redirect('/config')


def register_plugin():
    return blueprint, 'Home', 1
