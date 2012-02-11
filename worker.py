import json, time, urllib, urllib2

def get_work(url):
    u = urllib2.urlopen('%s/work'%url)
    return json.loads(u.read())

def submit_work(url, id, output):
    data = urllib.urlencode({'id':id, 'output':output})
    urllib2.urlopen('%s/receive_work'%url, data=data)

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
        id = w['id']
        print id, output
        submit_work(url, id, output)

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
