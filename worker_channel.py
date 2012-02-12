#!/usr/bin/env python
import json, time, urllib, urllib2, sys, logging, socket, os
import gae_channel
import multiprocessing
from Queue import Empty
import sage.all

DEBUG_LIST = [None,"local","cmd"]
DEBUG = DEBUG_LIST[1]

class SageCmdTest(object):
    def __init__(self):
        self.message_file = sys.argv[1]
    class logger(object):
        def warn(self, s):
            print s
    def long_poll_messages(self):
        with open(self.message_file) as F:
            for a in F.read().split("$$"):
                if len(a) > 0:
                    yield a
        with open(self.message_file,'w') as F:
            F.write("")

class SageLocalTest(object):
    def __init__(self):
        if len(sys.argv) > 1:
            self.id = sys.argv[1]
        else:
            self.id = "new-worker"
        data = urllib.urlencode({'id':self.id})
        urllib2.urlopen('http://localhost:9000/worker/login', data=data)
    class logger(object):
        def warn(self, s):
            print s
    def long_poll_messages(self):
        a = urllib2.urlopen('http://localhost:9000/fake_channel/%s'%(self.id)).read()
        while a:
            if DEBUG:
                print "RECEIVED: %s"%a
                print "RECEIVE TIME: %s"%(time.time())
            yield a
            a = urllib2.urlopen('http://localhost:9000/fake_channel/%s'%(self.id)).read()
        
class SageMonitor(object):
    def __init__(self, worker):
        self.worker = worker
        if DEBUG == "cmd":
            self.chan = SageCmdTest()
        elif DEBUG == "local":
            self.chan = SageLocalTest()
        else:
            self.chan = gae_channel.Client(worker.token)
            self.chan.logger.setLevel(logging.DEBUG)
        print "Listening with token %s"%(worker.token)
        self.checking = False
        self._reconnect_time = time.time()
        self._need_reconnect = False
        self._backoff = 1
        self.lpm = self.chan.long_poll_messages()

    def __iter__(self):
        while True:
            if self.checking:
                for userid, t in self.worker.checkup_times.items():
                    #print t, time.time()
                    curtime = time.time()
                    if curtime >= t:
                        self.worker.sessions[userid].query_status()
                self.checking = False
            try:
                try:
                    msg = self.lpm.next()
                    self._backoff = 1
                    self._need_reconnect = False
                    yield msg
                except StopIteration:
                    self.lpm = self.chan.long_poll_messages()
                    try:
                        msg = self.lpm.next()
                        self._backoff = 1
                        self._need_reconnect = False
                        yield msg
                    except StopIteration:
                        # No messages right now.
                        self.wait()
                        self.checking = True
            except gae_channel._TalkMessageCorrupted, e:
                self.chan.logger.warn('TalkMessageCorrupted: %s' % str(e))
                self.chan.logger.warn('reconnecting')
                yield self.next()
            except socket.error, e:
                # timeout (connection lost)
                self.logger.warn('Long poll timed out: %s' % e)
                self.logger.warn('reconnecting in %d seconds' % self._backoff )
                self._need_reconnect = True
                self._reconnect_time = time.time() + self._backoff
                if self._backoff < 32:
                    self._backoff *= 2
                self.checking = True
                self.wait()

    def wait(self):
        min_wait = .1
        curtime = time.time()
        for t in self.worker.checkup_times.itervalues():
            diff = t - curtime
            if diff < min_wait:
                min_wait = diff
        if self._need_reconnect:
            diff = self._reconnect_time - curtime
            if diff < min_wait:
                min_wait = diff
        if min_wait > 0:
            time.sleep(min_wait)

class SageGAEWorker(object):
    def __init__(self, worker_subdir = "worker/", \
                       delay = 0.02, checkup_interval = 0.01):
        if DEBUG == 'cmd':
            self.base_url = None
        elif DEBUG == 'local':
            self.base_url = "http://localhost:9000/"
        else:
            self.base_url = "http://simplesage389.appspot.com/"
        self.worker_subdir = worker_subdir
        self.delay = delay
        self.checkup_interval = checkup_interval
        self.sessions = {}
        self.checkup_times = {}
        if DEBUG:
            self.token = 0
        else:
            self.fetch_token()
        self.listen()
        
    def fetch_token(self):
        url = self.base_url + "worker/login"
        req = urllib2.urlopen(url, data=urllib.urlencode({}))
        self.token = req.read()

    def listen(self):
        self.monitor = SageMonitor(self)
        for msg in self.monitor:
            msg = json.loads(msg)
            cmd = msg['cmd']
            print "Handling %s command"%(cmd)
            if cmd == 'exec':
                self.exec_code(userid = msg['user_id'], cellid = msg['cell_id'], code = msg['input'])
            else:
                assert False

    def exec_code(self, userid, cellid, code):
        if DEBUG:
            print "userid = %s"%userid
        if self.sessions.has_key(userid):
            session = self.sessions[userid]
        else:
            session = self.fork_new_session(userid)
        code = prepare(code)
        session.execute(cellid, code)

    def fork_new_session(self, userid):
        new_session = SageSession(self, userid, self.delay, self.checkup_interval)
        self.sessions[userid] = new_session
        return new_session

    def post(self, userid, cellid, out, status):
        if DEBUG:
            print "POSTING: %s, %s, %s, %s"%(userid, cellid, out, status)
            print "POST TIME: %s"%(time.time())
        if DEBUG != "cmd":
            url = self.base_url + "workers/update"
            data = urllib.urlencode({'user_id':userid, 'cell_id':cellid, 'output':out, 'status':status})
            urllib2.urlopen(url, data=data)

def prepare(code):
    code = sage.all.preparse(code)
    if not code:
        return code
    newline_loc = code.rfind("\n")
    last_line = code[newline_loc+1:].strip()
    while last_line[0] == '#':
        code = code[:newline_loc]
        newline_loc = code.rfind("\n")
        last_line = code[newline_loc+1:].strip()
    if code[newline_loc+1] != " ":
        # the last line is an expression
        code = code[:newline_loc+1] + "print(" + code[newline_loc+1:] + ")"
    return code

class OutputStatus(object):
    def __init__(self, output, done):
        self.output = output
        self.done = done

class SageProcess(multiprocessing.Process):
    def __init__(self, delay = 0.02):
        multiprocessing.Process.__init__(self)
        self.output = os.tmpfile()
        self.done = os.tmpfile()
        self.input = multiprocessing.Queue()
        self.delay = delay
        self.globs = {}
        for ky, val in sage.all.__dict__.iteritems():
            self.globs[ky] = val

    def execute(self, code):
        print "Putting command"
        self.input.put(code)

    def output_status(self):
        self.done.seek(0)
        self.output.seek(0)
        done = self.done.read()
        output = self.output.read()
        if done:
            self.done.truncate(0)
            self.output.truncate(0)
        return OutputStatus(output, bool(done))

    def run(self):
        os.dup2(self.output.fileno(), sys.stdout.fileno())
        while True:
            try:
                code = self.input.get_nowait()
            except Empty:
                time.sleep(self.delay)
                continue
            sys.stderr.write("Pre-exec\n")
            sys.stderr.flush()
            exec code in self.globs
            sys.stderr.write("Post-exec\n")
            sys.stderr.flush()
            self.done.write("1")
            self.done.flush()

class SageSession(object):
    def __init__(self, worker, userid, delay, checkup_interval = 0.01):
        self.worker = worker
        self.userid = userid
        #from sagenb.interfaces.expect import WorksheetProcess_ExpectImplementation
        #self.expect = WorksheetProcess_ExpectImplementation()
        self.expect = SageProcess()
        self.expect.start()
        if DEBUG:
            print "Starting Sage"
        self.expect.execute("from sage.all import *\n")
        self.exec_queue = []
        self.checkup_interval = checkup_interval
        self.set_starting_intervals()
        self.cur_cellid = None
        self.output_len = 0

    def set_starting_intervals(self):
        if DEBUG:
            print "setting intervals"
        self.running = True
        self.post_interval = self.checkup_interval
        self.worker.checkup_times[self.userid] = self.next_post = time.time() + self.checkup_interval

    def clear_intervals(self):
        if DEBUG:
            print "clearing intervals"
        del self.worker.checkup_times[self.userid]
        self.running = False

    def execute(self, cellid, code):
        if DEBUG:
            print "executing %s"%code
        self.exec_queue.append((cellid, code))
        self.query_status(new=True) # starts execution if there's nothing in the exec_queue

    def _execute(self):
        self.cur_cellid, code = self.exec_queue.pop(0)
        if DEBUG:
            print "EXECUTE TIME: %s"%(time.time())
        self.expect.execute(code)
        self.output_len = 0
        self.set_starting_intervals()

    def query_status(self, new=False):
        status = self.expect.output_status()
        new_out = status.output[self.output_len:].strip()
        cur_cellid = self.cur_cellid
        running = self.running
        #print "running %s"%self.running
        if new or status.done:
            if len(self.exec_queue) > 0:
                print "Nonempty exec queue"
                self._execute()
            else:
                self.clear_intervals()
            if running and cur_cellid is not None: # cur_cellid is None for the initial import
                if DEBUG:
                    print "status %s"%status.output
                self.worker.post(self.userid, cur_cellid, new_out, 'done')
            elif DEBUG:
                print "Sage Import complete"
        elif new_out and time.time() > self.next_post:
            self.output_len = len(status.output)
            self.worker.post(self.userid, cur_cellid, new_out, 'working')
            if self.post_interval < self.checkup_interval * 32:
                self.post_interval *= 2
            self.next_post = time.time() + self.post_interval            

if __name__ ==  '__main__':
    SageGAEWorker()
