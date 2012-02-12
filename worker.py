import json, time, urllib, urllib2

def get_work(url):
    u = urllib2.urlopen('%s/workers/work'%url)
    return json.loads(u.read())

def submit_work(url, cell_id, user_id, output):
    data = urllib.urlencode({'cell_id':cell_id, 'user_id':user_id, 'output':output,
                             'status':'done'})
    urllib2.urlopen('%s/workers/update'%url, data=data)

def do_work(url='http://localhost:9000'):
    todo = get_work(url)
    if len(todo) == 0:
        return
    print "Doing %s tasks"%len(todo)
    from sage.all import sage_eval
    for w in todo:
        try:
            output = sage_eval(w['input'])
        except Exception, msg:
            output = "Error: '%s'"%msg
        user_id = w['user_id']
        cell_id = w['cell_id']
        print user_id, cell_id, output
        submit_work(url, cell_id, user_id, output)

def go(url='http://localhost:9000', delay=0.5):
    while True:
        do_work(url)
        time.sleep(delay)

        
if __name__ ==  '__main__':
    import sys
    if len(sys.argv) > 1:
        go(sys.argv[1])
    else:
        go()
