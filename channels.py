"""
    :copyright: (c) 2012 by William Stein
    :license: BSD, see LICENSE for more details.
"""

import logging
from flask import request
from simplesage import app

@app.route('/_ah/channel/connected/', methods=['POST'])
def channel_connected():
    client_id = request.form['from']
    logging.info('client %s connected' % client_id)
    return ''

@app.route('/_ah/channel/disconnected/', methods=['POST'])
def channel_disconnected():
    client_id = request.form['from']
    logging.info('client %s disconnected' % client_id)
    return ''
