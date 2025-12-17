import sqlite3
from flask import current_app, g
import numpy as np
import io

def adapt_matrix(arr):
    out = io.BytesIO()
    np.save(out, arr, allow_pickle=False)
    out.seek(0)
    return sqlite3.Binary(out.read())

def convert_matrix(text):
    out = io.BytesIO(text)
    out.seek(0)
    return np.load(out, allow_pickle=False)

def get_db():
    if 'db' not in g:
        print(f"Connecting to database... {current_app.config['DATABASE']}")
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    return g.db

def query_db(query, args=(), one=False):
    conn = get_db()
    cur = conn.execute(query, args)
    conn.commit()
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()

def init_db():
    db = get_db()

    with current_app.open_resource('schemas.sql') as f:
        db.executescript(f.read().decode('utf8'))

def init_app(app):
    sqlite3.register_adapter(np.ndarray, adapt_matrix)
    sqlite3.register_converter("matrix", convert_matrix)

    app.teardown_appcontext(close_db)
