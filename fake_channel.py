"""
    :copyright: (c) 2012 by William Stein
    :license: BSD, see LICENSE for more details.
"""

from google.appengine.ext import db

class Channels(db.Model):
    id = db.StringProperty()
    msg = db.ListProperty(unicode)

import logging

def create_channel(id):
    # create new entry in database for channel with this id, if it doesn't exist
    q = Channels.all()
    logging.info("id = '%s'"%id)
    c = q.filter("id =", id).get()
    if c is None:
        c = Channels(id = id, msg = [])
    else:
        # already have such a channel  # TODO -- how should we really check that this is not empty!?
        logging.info("found one")
        c.msg = []
    c.put()
    return '0'


def send_message(id, msg):
    # insert into database msg with given id
    q = Channels.all()
    c = q.filter("id =", id).get()
    if c is None:
        raise RuntimeError, "channel %s is not opened"%id
    c.msg.insert(0, unicode(msg))
    c.put()

from simplesage import app

@app.route('/fake_channel/<id>')
def fake_channel(id):
    q = Channels.all()
    c = q.filter("id =", id).get()
    if not c:
        return ''
    if len(c.msg) > 0:
        msg = c.msg.pop()
        c.put()
        return msg
    else:
        return ''
    
from flask import render_template, redirect

@app.route('/db/fake_channels/')
def db_fake_channels():
    channels = Channels.all()
    return render_template('db_fake_channels.html', **locals()) 
        
@app.route('/db/fake_channels/drop')
def drop():
    from fake_channel import Channels
    for a in Channels.all():
        a.delete()
    return redirect('db/fake_channels')


    

