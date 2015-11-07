from flask import render_template, Blueprint, flash, redirect
from myflexget import app_folder
import os


blueprint = Blueprint('logs', __name__, url_prefix='/logs', template_folder='templates', static_folder='static')


#Populate leftbar with log files:
@blueprint.context_processor
def variables():
    _leftbar = []
    files = os.listdir(os.path.join(app_folder, 'tmp'))
    for f in sorted(files):
        if f.endswith('.log') or f.endswith('.txt'):
            _leftbar.append({'href': '/logs/'+f, 'caption': f})
    return {'leftbar': _leftbar}


@blueprint.route('')
def index():
    return render_template('logs_logs.html')


@blueprint.route('/<logfile>')
def logfile(logfile):
    log_file = os.path.join(app_folder, 'tmp', logfile)
    if os.access(log_file, os.R_OK):
        f = open(log_file, 'r')
        content = f.read().decode('utf-8')
        f.close()
    else:
        content = ''

    return render_template('logs_logs.html', content=content, logfile=logfile)


@blueprint.route('/clear/<logfile>')
def logfile_clear(logfile):
    log_file = os.path.join(app_folder, 'tmp', logfile)
    if not os.path.isfile(log_file):
        flash('Not a valid log file: %s' % log_file)
    else:
        if os.access(log_file, os.W_OK):
            open(log_file, 'w').close()
            flash('Cleared logfile: %s' % log_file)
        else:
            flash('Permission error while clearing logfile: %s' % log_file)

    return redirect('/logs/%s' % logfile)


def register_plugin():
    return blueprint, 'Logs', 255
