
import cgi
import webapp2
from google.appengine.ext import db



navbar = """
<a href="/">home</a>&nbsp;&nbsp;
<a href="/input">input</a>&nbsp;&nbsp;
<a href="/output">output</a>&nbsp;&nbsp;
<a href="/work">work</a>&nbsp;&nbsp;
<a href="/enter_work">enter work</a>&nbsp;&nbsp;
<a href="/receive_work">receive work</a>
<br>
<hr>
"""

class MainPage(webapp2.RequestHandler):
    def get(self):
        self.response.out.write("""
          <html>
            <body>
            %s
              <form action="/input" method="post">
                <div><textarea name="content" rows="6" cols="70"></textarea></div>
                <div><input type="submit" value="Evaluate Sage Code"></div>
              </form>
            </body>
          </html>"""%navbar)

class Input(webapp2.RequestHandler):
    def post(self):
        c = cgi.escape(self.request.get('content'))
        self.response.out.write("""
        <html><body>%s
        Received request to compute '%s'
        <br>
        <a href="output">output</a>
        </body></html>
        """%(navbar, c))

class Output(webapp2.RequestHandler):
    def get(self):
        self.response.out.write("""
        ID = 1
        <br>
        OUTPUT = 4

        <br><br>
        <a href="/">new input</a>
        """)

class Work(webapp2.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write(
"""{0:'2+2'}""")

class EnterWork(webapp2.RequestHandler):
    def get(self):
        self.response.out.write("""
          <html>
            <body>
            %s
              <form action="/receive_work" method="post">
                <div><textarea name="id" rows="1" cols="10"></textarea></div>
                <div><textarea name="content" rows="6" cols="70"></textarea></div>
                <div><input type="submit" value="Submit Work"></div>
              </form>
            </body>
          </html>"""%navbar)
        
class ReceiveWork(webapp2.RequestHandler):
    def post(self):
        c = cgi.escape(self.request.get('content'))
        i = cgi.escape(self.request.get('id'))        
        self.response.out.write("""
        <html><body>%s        
        Result: id=%s, output=%s
        <br>
        <a href="work">work</a>
        </body></html>
        """%(navbar,i, c))

app = webapp2.WSGIApplication([('/', MainPage),
                               ('/input', Input),
                               ('/output', Output),
                               ('/work', Work),
                               ('/enter_work', EnterWork),
                               ('/receive_work', ReceiveWork)
                               ],
                              debug=True)
