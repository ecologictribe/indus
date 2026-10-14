import sqlite3
import os
from flask import g
from config import Config

def get_db():
    """Returns the database connection (using Flask g context if available, or direct connection)."""
    from flask import has_app_context
    if has_app_context():
        if 'db' not in g:
            if not os.path.exists(Config.DB_PATH):
                from data_loader import load_data
                load_data(Config.DB_PATH)
                
            g.db = sqlite3.connect(Config.DB_PATH)
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON;")
        return g.db
    else:
        conn = sqlite3.connect(Config.DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

def close_db(e=None):
    """Closes database connection at the end of request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    """Convenience helper to query the database."""
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def execute_db(query, args=()):
    """Convenience helper to execute insert/update/delete."""
    db = get_db()
    cur = db.execute(query, args)
    db.commit()
    last_id = cur.lastrowid
    cur.close()
    return last_id
