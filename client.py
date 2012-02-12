import logging
from flask import request, jsonify
from google.appengine.api import channel
from simplesage import app
import simplejson

@app.route('/input_new', methods=['POST'])
def input_new():
    json_load = simplejson.loads(request.form['json'])
    logging.info('input received', json_load)
    return jsonify({'status': 'ok'})

@app.route('/fake_worker', methods=['GET'])
def fake_worker():
    userid = request.args.get('userid')
    newoutput = request.args.get('newoutput')
    return push_to_client(userid, newoutput)

def push_to_client(userid, newoutput):
    json = simplejson.dumps({'cellid': 0,
                             'userid': userid,
                             'newoutput': newoutput,
                             'status': 'more'})
    channel.send_message(userid, json)
    return 'ok' 
