import cgi
import json
import webapp2
from google.appengine.ext import db



navbar = """
<a href="/">submit</a>&nbsp;&nbsp;&nbsp;
<a href="/database">database</a>&nbsp;&nbsp;&nbsp;
<a href="/submit_work">submit work</a>
<br>
<hr>
"""

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

class MainPage(webapp2.RequestHandler):
    def get(self):
        self.response.out.write("""
          <html>
            <body>
            %s
            <br>
            Enter a Sage expression:
              <form action="/input" method="post">
                <div><input type="text" name="input" size="90"></div>
              </form>
            </body>
          </html>"""%navbar)

class Input(webapp2.RequestHandler):
    def post(self):
        id = next_id()
        input = cgi.escape(self.request.get('input'))
        
        wr = WorkRequest(parent=key, id=id, input=input)
        wr.put()

        self.response.out.write("""
        <html><body>%s
        id = %s<br>
        input = '%s'
        <br>
        %s
        </body></html>
        """%(navbar, id, input, db_table()))

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
    

class Database(webapp2.RequestHandler):
    def get(self):
        self.response.out.write("""
        %s
        <h2>Database</h2>
        %s
        """%(navbar, db_table()))

class Work(webapp2.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'
        all_work = db.GqlQuery("SELECT * FROM WorkRequest")
        # TODO: should only query for things with output none!
        s = json.dumps([{'id':a.id, 'input':a.input} for a in all_work if a.output is None])
        self.response.out.write(s)

class SubmitWork(webapp2.RequestHandler):
    def get(self):
        self.response.out.write("""
          <html>
            <body>
            %s
              <form action="/receive_work" method="post">
                <div>id:<br><textarea name="id" rows="1" cols="10"></textarea></div>
                <div>output:<br><textarea name="output" rows="6" cols="70"></textarea></div>
                <div><input type="submit" value="Submit Work"></div>
              </form>
            </body>
          </html>"""%navbar)
        
class ReceiveWork(webapp2.RequestHandler):
    def post(self):
        output = cgi.escape(self.request.get('output'))
        id = int(cgi.escape(self.request.get('id')))
        self.response.out.write("""
        <html><body>%s        
        Result: id=%s, output=%s
        </body></html>
        """%(navbar,id, output))

        for a in db.GqlQuery("SELECT * FROM WorkRequest WHERE id=%s"%id):
            a.output = output
            a.put()
        

app = webapp2.WSGIApplication([('/', MainPage),
                               ('/input', Input),
                               ('/database', Database),
                               ('/work', Work),
                               ('/submit_work', SubmitWork),
                               ('/receive_work', ReceiveWork)
                               ],
                              debug=True)
