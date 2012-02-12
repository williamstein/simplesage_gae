import logging
from flask import request, jsonify, g
from google.appengine.api import channel
from simplesage import app, Cells, login_required, next_cell_id
import json

@app.route('/input_new', methods=['POST'])
@login_required
def input_new():
    json_load = json.loads(request.form['json'])
    
    cell = Cells(user_id = g.user.user_id(),
                 cell_id = next_cell_id(),
                 input   = json_load['input'])
    cell.put()
    
    logging.info('input received: %s'%json_load)
    return jsonify({'status': 'ok'})

@app.route('/fake_worker', methods=['GET'])
def fake_worker():
    userid = request.args.get('userid')
    newoutput = request.args.get('newoutput')
    return push_to_client(userid, newoutput)

def push_to_client(userid, newoutput):
    json = json.dumps({'cellid': 0,
                             'userid': userid,
                             'newoutput': newoutput,
                             'status': 'more'})
    channel.send_message(userid, json)
    return 'ok' 
