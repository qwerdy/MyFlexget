from myflexget import app
from flask import g
import sqlite3
import os

#Get absolute path to database file:
dir_path = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(dir_path, 'db.sqlite')

#Create database if not exist
if not os.access(DATABASE, os.R_OK):
    print('INFO: No database found, creating one')
    db = sqlite3.connect(DATABASE)
    db.cursor().executescript(open(os.path.join(dir_path, 'schema.sql'), 'r').read())
    db.commit()
    db.close()


def db_get():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db


def db_get_raw():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db


def db_query(query, args=(), one=False):
    cur = db_get().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


def db_execute(query, args=()):
    db = db_get()
    cur = db.execute(query, args)
    db.commit()
    cur.close()


def db_get_settings(what):
    settings = {}
    for x in db_query('select * from settings_new where id="%s"' % what):
        settings[x['key']] = x['value']
    return settings


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.commit()
        db.close()
