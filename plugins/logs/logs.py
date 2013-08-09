from flask import render_template, Blueprint
from myflexget import register_plugin, app_folder
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
        content = f.read()
        f.close()
    else:
        content = ''

    return render_template('logs_logs.html', content=content)


register_plugin(blueprint, menu='Logs', order=255)
