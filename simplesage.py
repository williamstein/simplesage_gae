from flask import Flask, request, redirect, url_for, g
app = Flask(__name__)

from google.appengine.ext import db
from google.appengine.api import users

from flask import render_template

import cgi
import json
import urllib2


##############################
# decorators
##############################

# makes it so "g.user" is defined and not None
# (put this after @app.route)
def login_required(f):
    def wrapper(*args, **kwds):
        if not hasattr(g, 'user') or not g.user:
            # Get the current user, or redirect them to a login page
            user = users.get_current_user()
            if user is None:
                return redirect(users.create_login_url(request.path))
            g.user = user
        return f(*args, **kwds)
    return wrapper

##############################
# database
##############################

class Cells(db.Model):
    user_id = db.StringProperty()
    cell_id = db.IntegerProperty()
    input = db.StringProperty(multiline=True)
    output = db.StringProperty(multiline=True)
    status = db.StringProperty()   # 'run', 'done'

class Workers(db.Model):
    worker_id = db.StringProperty()

class Sessions(db.Model):
    worker_id = db.StringProperty()
    user_id = db.StringProperty()
    status = db.StringProperty()

@login_required   
def next_cell_id():
    q = Cells.all()
    q.filter("user_id =", g.user.user_id())
    q.order("-cell_id")
    for a in q:
        return a.cell_id + 1
    return 0

##############################
# handling URL's
##############################

@app.route("/")
def main_page():
    return render_template('main.html')

@app.route('/input', methods=['POST'])
@login_required   
def input_page():
    cell = Cells(user_id = g.user.user_id(),
                 cell_id = next_cell_id(),
                 input   = cgi.escape(request.form['input']))
    cell.put()
    return redirect('/db/cells')

@login_required
def get_all_cells():
    q = Cells.all()
    q.filter("user_id =", g.user.user_id())
    q.order('-cell_id')
    return q

@app.route('/db/cells')
def db_cells():
    all_cells = get_all_cells()
    return render_template('db_cells.html', **locals()) 

@app.route('/db/workers')
def db_workers():
    all_workers = Workers.all()
    return render_template('db_workers.html', **locals()) 

@app.route('/db/sessions')
def db_sessions():
    all_sessions = Sessions.all()
    return render_template('db_sessions.html', **locals()) 

@app.route("/workers/work")
def work():
    q = Cells.all()
    q.filter('status !=', 'done')
    w = [{'cell_id':a.cell_id, 'user_id':a.user_id, 'input':a.input} for a in q]
    return json.dumps(w)

@app.route("/workers/submit")
def submit_work():
    user = users.get_current_user()
    if user is not None:
        user_id = user.user_id()
    return render_template('submit_work.html', **locals())

@app.route('/workers/update', methods=['POST'])
def workers_update():
    output = cgi.escape(request.form['output'])
    cell_id = int(cgi.escape(request.form['cell_id']))
    user_id = cgi.escape(request.form['user_id'])
    status = cgi.escape(request.form['status'])

    q = Cells.all()
    q.filter('cell_id =', cell_id)
    q.filter('user_id =', user_id)
    for a in q:
        if a.output is None:
            a.output = output
        else:
            a.output += output
        a.status = status
        a.put()

    return 'success'
