import logging
from flask import request, jsonify
from google.appengine.api import channel
from simplesage import app
import simplejson
import random

@app.route('/worker/login', methods=['POST'])
def login():
    id = str(get_new_worker_id())
    token = channel.create_channel(id)  
    return token

def get_new_worker_id():
    return random.randint(0, 100) 
