import logging
from flask import request, jsonify, g
from simplesage import app, Cells, Sessions, Workers, login_required, next_cell_id
import json

from google.appengine.api import channel

@app.route('/input_new', methods=['POST'])
@login_required
def input_new():
    input = request.form['input']
    logging.info('input received %s' % input)
    user_id = g.user.user_id()
    cell = Cells(user_id = user_id,
                 cell_id = next_cell_id(),
                 input   = input)
    cell.put()
    send_work(user_id, cell.cell_id, cell.input)
    return jsonify({'status': 'ok'})

@app.route('/fake_worker', methods=['GET'])
def fake_worker():
    userid = request.args.get('userid')
    newoutput = request.args.get('newoutput')
    return push_to_client(userid, newoutput)

def push_to_client(cell_id, user_id, new_output):
    msg = json.dumps({'cellid': str(cell_id),
                      'userid': user_id,
                      'newoutput': new_output,
                      'status': 'more'})
    channel.send_message(user_id, msg)
    return 'ok'

def get_worker(user_id):
    q = Sessions.all()
    for g in q.filter('user_id =', user_id):
        # TODO: We whould check further here that g is a valid session.
        return g.worker_id

    # We must find a ready worker and assign it to this user:
    q = Workers.all()
    for g in q.filter('status =', 'available'):
        # make a new session using that worker for this user_id
        s = Sessions(worker_id=g.worker_id, status='assigned', user_id=user_id)
        s.put()
        # set that worker's status as assigned (so no longer available)
        g.status = 'assigned'
        g.put()
        
        return g.worker_id

    # No worker available
    raise RuntimeError, "no workers available"


import fake_channel

def send_work(user_id, cell_id, input):
    # 1. Get worker allocated to this user (or allocate one)
    worker_id = get_worker(user_id)

    # 2. Send message
    msg = json.dumps( {'cell_id':cell_id, 'user_id':user_id, 'input':input} )

    logging.info('sending message to %s: %s' % (worker_id, msg))
    
    fake_channel.send_message(worker_id, msg)

    
    
