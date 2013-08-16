from flask import render_template, Blueprint
from myflexget import app_folder
import os
import sqlite3

blueprint = Blueprint('flexget', __name__, url_prefix='/flexget', template_folder='templates')


def db_execute(query, args=()):
    if not os.access(_db_file, os.R_OK):
        return None

    fg_db = sqlite3.connect(_db_file)
    fg_db.row_factory = sqlite3.Row
    result = fg_db.execute(query, args).fetchall()
    fg_db.close()
    return result


_leftbar = []
_leftbar.append({'href': '/flexget/history', 'caption': '<b>Flexget History</b>'})

_db_file = os.path.join(app_folder, 'tmp', 'db-testconfig.sqlite')

shows = db_execute('select * from series order by name')
if shows:
    for show in shows:
        _leftbar.append({'href': '/flexget/'+str(show['id']), 'caption': show['name']})


@blueprint.context_processor
def variables():
    return {'leftbar': _leftbar}


@blueprint.route('')
def index():
    recent = db_execute('SELECT * FROM series_episodes AS se JOIN episode_releases AS er WHERE se.id = er.episode_id ORDER BY er.first_seen DESC LIMIT 25') or []
    return render_template('flexget_flexget.html', leftbar=_leftbar, info=recent)


@blueprint.route('/<int:show_id>')
def show(show_id):
    show = db_execute('SELECT * FROM series_episodes AS se JOIN episode_releases AS er WHERE se.id = er.episode_id AND se.series_id = ? ORDER BY se.identifier DESC, er.downloaded DESC', [show_id]) or []
    return render_template('flexget_flexget.html', leftbar=_leftbar, info=show)


@blueprint.route('/history')
def history():
    show = db_execute('SELECT * FROM history ORDER BY time DESC LIMIT 25') or []
    return render_template('flexget_history.html', leftbar=_leftbar, info=show)


def register_plugin():
    return blueprint, 'Flexget'
