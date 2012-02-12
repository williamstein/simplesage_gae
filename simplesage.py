from flask import Flask, request
app = Flask(__name__)

from google.appengine.ext import db
from flask import render_template

import cgi
import json
import urllib2

##############################
# database
##############################

class WorkRequest(db.Model):
    id = db.IntegerProperty()
    input = db.StringProperty(multiline=True)
    output = db.StringProperty(multiline=True)
    date = db.DateTimeProperty(auto_now_add=True)

key = db.Key.from_path('work', 'request')

def next_id():
    for a in db.GqlQuery("SELECT * from WorkRequest ORDER by id DESC"):
        return a.id + 1
    return 0

##############################
# handling URL's
##############################


@app.route("/")
def main_page():
    return render_template('main.html')

@app.route('/input', methods=['POST'])
def input_page():
    id = next_id()
    input = cgi.escape(request.form['input'])
    all_work = get_all_work() 

    wr = WorkRequest(parent=key, id=id, input=input)
    wr.put()

    return render_template('input.html', **locals()) 

def get_all_work():
    return db.GqlQuery("SELECT * FROM WorkRequest ORDER BY date DESC")

@app.route("/database")
def database():
    return render_template('database.html', all_work = get_all_work())

@app.route("/submit_work")
def submit_work():
    return render_template('submit_work.html')

@app.route("/work")
def work():
    all_work = db.GqlQuery("SELECT * FROM WorkRequest")
    # TODO: should only query for things with output none!
    return json.dumps([{'id':a.id, 'input':a.input} for a in all_work if a.output is None])


@app.route('/receive_work', methods=['POST'])
def receive_work():
    output = cgi.escape(request.form['output'])
    id = int(cgi.escape(request.form['id']))

    for a in db.GqlQuery("SELECT * FROM WorkRequest WHERE id=%s"%id):
        a.output = output
        a.put()

    return render_template('receive_work.html', **locals())
