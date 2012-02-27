"""
    :copyright: (c) 2012 by William Stein
    :license: BSD, see LICENSE for more details.
"""

import cgi

import logging
from flask import request, jsonify

#from google.appengine.api import channel
import fake_channel as channel

from simplesage import app, Workers
import random

@app.route('/worker/login', methods=['POST'])
def login():
    #id = str(get_new_worker_id())
    id = cgi.escape(request.form['id'])
    token = channel.create_channel(id)

    # record that we have this new worker and it is ready to go
    for g in Workers.all().filter('worker_id =', id):
        g.status = 'available'
        g.put()
        return token
    else:
        w = Workers(worker_id=id, status='available')
        w.put()
    return token

def get_new_worker_id():
    return random.randint(0, 100) 
