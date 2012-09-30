import web

db = web.database(dbn='sqlite', db='db.sqlite')

def get_shows(clean=False):
    if not clean:
        return db.select('shows', order='name')
    else:
        return db.select('shows', order='name', what='name')

#Returns shows feed_name:
def get_shows_dir():
    shows = db.select('shows', order='name')
    show_dir = {}
    for show in shows:
        show_dir[show['name']] = show['feed_name']
    return show_dir

def get_hq_shows_list():
    shows = db.select('shows', where='hq = 1')
    hq_shows = []
    for show in shows:
        hq_shows.append(show['name'])
    return hq_shows

def get_ignored_shows_list():
    shows = db.select('shows', where='ignore = 1')
    ig_shows = []
    for show in shows:
        ig_shows.append(show['name'])
    return ig_shows

def get_show(name):
    return db.query("SELECT * FROM shows WHERE name = $name LIMIT 1", vars=locals())

def get_times():
    return db.select('settings', what='fetch_start, fetch_end')

def set_times(start, end):
    db.query('UPDATE settings set fetch_start=$start, fetch_end=$end', vars=locals())

def new_show(name, feed_name, hq, ignore):
    db.insert('shows', name=name, feed_name=feed_name, hq=hq, ignore=ignore)

def update_show(id, name, feed_name, hq, ignore):
    db.update('shows', where='id = $id', name=name, feed_name=feed_name, hq=hq, ignore=ignore, vars=locals())

def delete_show(id):
    db.delete('shows', where='id=$id', vars=locals())

def get_settings():
    return db.select('settings')

def get_credentials():
    return db.select('settings', what='myusername, mypassword')

def set_credentials(username, password):
    db.query("UPDATE settings set myusername=$username, mypassword=$password", vars=locals())

def set_settings(email, rss, flexget, path, dq, hq, lm):
    db.query("UPDATE settings set email=$email, rssfeed=$rss, flexget=$flexget, downloadpath=$path, def_quality=$dq, high_quality=$hq, limit_number=$lm", vars=locals())
