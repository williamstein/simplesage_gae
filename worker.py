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

def do_work(url, id):
    w = get_work(url, id)
    if not w:
        return 
    print "Doing task: %s"%w
    from sage.all import sage_eval
    try:
        output = sage_eval(w['input'])
    except Exception, msg:
        output = "Error: '%s'"%msg
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
        do_work(url, id)
        time.sleep(delay)

        
if __name__ ==  '__main__':
    import sys
    if len(sys.argv) > 2:
        go(sys.argv[1], id=sys.argv[2])
    elif len(sys.argv) > 1:
        go(sys.argv[1], 'worker')
    else:
        go()
