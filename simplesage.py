from flask import Flask, request
app = Flask(__name__)

from google.appengine.ext import db

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

navbar = """
Flask Simple Sage Notebook Demo<br><br>
<a href="/">submit</a>&nbsp;&nbsp;&nbsp;
<a href="/database">database</a>&nbsp;&nbsp;&nbsp;
<a href="/submit_work">submit work</a>
<br>
<hr>
"""

@app.route("/")
def main_page():
    return """
          <html>
            <body>
            %s
            <br>
            Enter a Sage expression:
              <form action="/input" method="post">
                <div><input type="text" name="input" size="90"></div>
              </form>
            </body>
          </html>"""%navbar

@app.route('/input', methods=['POST'])
def input_page():
    id = next_id()
    input = cgi.escape(request.form['input'])

    wr = WorkRequest(parent=key, id=id, input=input)
    wr.put()

    return """
    <html><body>%s
    id = %s<br>
    input = '%s'
    <br>
    %s
    </body></html>
    """%(navbar, id, input, db_table())

def db_table():
    all_work = db.GqlQuery("SELECT * FROM WorkRequest ORDER BY date DESC")
    s = '<table border=1>'
    s += '<tr><th>Date</th><th width=100>id</th><th width=150>input</th><th>output</th></tr>\n'
    for a in all_work:
        if a.output is None:
            code = 'bgcolor="yellow"'
        else:
            code = 'bgcolor="#eee"'
        s += '<tr %s><td>'%code + '</td><td>'.join([
            str(a.date.ctime()), str(a.id),
            '<pre>'+str(a.input)+'</pre>',
            '<pre>' + str(a.output) + '</pre>']) + '</td></tr>\n'
    s += '</table>'
    return s

@app.route("/database")
def database():
    return """
    <html><body>
    %s
    <h2>Database</h2>
    %s
    </body></html>
    """%(navbar, db_table())

@app.route("/submit_work")
def submit_work():
    return """
          <html>
            <body>
            %s
              <form action="/receive_work" method="post">
                <div>id:<br><textarea name="id" rows="1" cols="10"></textarea></div>
                <div>output:<br><textarea name="output" rows="6" cols="70"></textarea></div>
                <div><input type="submit" value="Submit Work"></div>
              </form>
            </body>
          </html>"""%navbar

                
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

    return """
        <html><body>%s        
        Result: id=%s, output=%s
        </body></html>
        """%(navbar, id, output)
