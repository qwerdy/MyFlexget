from flask import render_template, Blueprint, request, flash, redirect
import utils.session as sess
from plugins.db import db_query, db_execute


blueprint = Blueprint('shows', __name__, url_prefix='/shows', template_folder='templates', static_folder='static')


@blueprint.context_processor
def variables():
    return {'info': None}


def get_show_list():
    #types: 0 = normal, 1 = hq, 2 = ignored, 3 = hq ignored
    shows = []
    for show in db_query('select * from shows order by name'):
        type = 1 if show['hq'] == 1 else 0
        if show['ignore'] == 1:
            type += 2
        shows.append({'name': show['name'], 'type': type, 'id': show['id']})
    return shows


@blueprint.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        name = request.form.get('name', '')
        if not name:
            flash('Name field is mandatory!', 'error')
        else:
            hq = 1 if request.form.get('hq', '') else 0
            ignore = 1 if request.form.get('ignore', '') else 0
            feed_name = request.form.get('feed_name', '')
            id = request.form.get('id', '')

            if id:  # update show
                db_execute('update shows set name=?, feed_name=?, hq=?, ignore=? where id=?', [name, feed_name, hq, ignore, id])
                flash('Added show %s' % request.form['name'])
            else:  # new show
                db_execute('insert into shows (name, feed_name, hq, ignore) values (?, ?, ?, ?)', [name, feed_name, hq, ignore])
                flash('Added show %s' % request.form['name'])
        #model.new_show(params.name, params.feed_name, hq, ignore)
    shows = get_show_list()
    return render_template('shows_shows.html', shows=shows)


@blueprint.route('/<int:showid>', methods=['GET', 'POST'])
def shows(showid):
    info = db_query('select * from shows where id=? limit 1', [showid], one=True)
    shows = get_show_list()
    return render_template('shows_shows.html', shows=shows, info=info)


@blueprint.route('/delete/<int:showid>')
def delete(showid):
    db_execute('delete from shows where id=?', [showid])
    flash('Deleted show with id %s' % showid)
    return redirect('/shows/')


@blueprint.route('/ajax/<request>')
def ajax(request):
    if request == 'showlist':
        if sess.myep is None or not sess.myep.logged_in():
            return render_template('shows_ajax_shows.html', authed=False)
        else:
            shows = sess.myep.get_myShows()
            return render_template('shows_ajax_shows.html', shows=shows, authed=True)
    else:
        return render_template('shows_ajax_shows.html')


def register_plugin():
    return blueprint, 'Shows', 2
