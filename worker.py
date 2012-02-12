import json, time, urllib, urllib2

## def get_work(url):
##     u = urllib2.urlopen('%s/workers/work'%url)
##     return json.loads(u.read())

def get_work(url, id):
    u = urllib2.urlopen('%s/fake_channel/%s'%(url, id)).read()
    if not u:
        return []
    return json.loads(u)

def submit_work(url, cell_id, user_id, output):
    data = urllib.urlencode({'cell_id':cell_id, 'user_id':user_id, 'output':output,
                             'status':'done'})
    urllib2.urlopen('%s/workers/update'%url, data=data)

from sagenb.interfaces.reference import execute_code
G = {}
execute_code('from sage.all import *', G)

def evaluate(input):
    from sage.all import preparse
    try:
        return execute_code(preparse(input), G)[0]
    except Exception, msg:
        return "Error: '%s'"%msg


def do_work(url, id):
    w = get_work(url, id)
    if not w:
        return 
    print "Doing task: %s"%w
    output = evaluate(w['input'])
    user_id = w['user_id']
    cell_id = w['cell_id']
    print user_id, cell_id, output
    submit_work(url, cell_id, user_id, output)

def login(url, id):
    data = urllib.urlencode({'id':id})
    urllib2.urlopen('%s/worker/login'%url, data=data)

def go(url='http://localhost:9000', delay=0.5, id='worker'):
    login(url, id)
    while True:
        try:
            do_work(url, id)
        except Exception, msg:
            print "Error: %s"%msg
            print "Waiting 5 secods"
            time.sleep(5)
        else:
            time.sleep(delay)

        
if __name__ ==  '__main__':
    import sys
    if len(sys.argv) > 2:
        go(sys.argv[1], id=sys.argv[2])
    elif len(sys.argv) > 1:
        go(sys.argv[1], 'worker')
    else:
        go()
