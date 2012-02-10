import cgi
import webapp2

class MainPage(webapp2.RequestHandler):
    def get(self):
        self.response.out.write("""
          <html>
            <body>
              <form action="/input" method="post">
                <div><textarea name="content" rows="6" cols="70"></textarea></div>
                <div><input type="submit" value="Evaluate Sage Code"></div>
              </form>
            </body>
          </html>""")

class Input(webapp2.RequestHandler):
    def post(self):
        c = cgi.escape(self.request.get('content'))
        self.response.out.write("""
        Received request to compute '%s'
        """%)


class Output(webapp2.RequestHandler):
    def get(self):
        self.response.out.write("""
        ID = 1
        OUTPUT = 4
        """)

app = webapp2.WSGIApplication([('/', MainPage),
                               ('output', Output),
                               ],
                              debug=True)
