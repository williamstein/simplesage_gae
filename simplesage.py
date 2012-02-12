from flask import Flask, request, redirect, url_for, g
app = Flask(__name__)

from google.appengine.ext import db
from google.appengine.api import channel
from google.appengine.api import users

from flask import render_template

import cgi
import json
import urllib2
import random
from functools import wraps

##############################
# decorators
##############################

# makes it so "g.user" is defined and not None
# (put this after @app.route)
def login_required(f):
    @wraps(f)
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
    input = db.TextProperty()
    output = db.TextProperty()
    status = db.StringProperty()   # 'run', 'done'

class Workers(db.Model):
    worker_id = db.StringProperty()
    status = db.StringProperty()

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
@login_required
def main_page():
    user_id = g.user.user_id()
    token = channel.create_channel(user_id)
    q = Cells.all()
    q.filter("user_id =", user_id)
    q.order("cell_id")
    return render_template('index.html', **locals())

@app.route('/submit')
def submit():
    return render_template('main.html')

@app.route("/get_channel_token", methods=['GET', 'POST'])
@login_required
def get_channel_token():
    token = channel.create_channel(g.user.user_id())
    return token

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

@app.route('/db/cells/drop')
def drop_cells():
    for a in Cells.all():
        a.delete()
    return redirect(url_for('db_cells'))

@app.route('/db/workers')
def db_workers():
    all_workers = Workers.all()
    return render_template('db_workers.html', **locals()) 

@app.route('/db/workers/drop')
def drop_workers():
    for a in Workers.all():
        a.delete()
    return redirect('db/workers')

@app.route('/db/sessions')
def db_sessions():
    all_sessions = Sessions.all()
    return render_template('db_sessions.html', **locals())

@app.route('/db/sessions/drop')
def drop_sessions():
    for a in Sessions.all():
        a.delete()
    return redirect('db/sessions')

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
    
    from client import push_to_client
    
    push_to_client(cell_id, user_id, output)
    
    for a in q:
        if a.output is None:
            a.output = output
        else:
            a.output += output
        a.status = status
        a.put()

    return 'success'

#############

import channels
import client
import worker_handler
import fake_channel
