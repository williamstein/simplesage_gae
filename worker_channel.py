#!/usr/bin/env python
import json, time, urllib, urllib2, sys, logging, socket, os
import gae_channel
import multiprocessing
from Queue import Empty

from sage.all import preparse

DEBUG = True

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

class SageMonitor(object):
    def __init__(self, worker):
        self.worker = worker
        if DEBUG:
            self.chan = SageCmdTest()
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
        min_wait = 60
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
    def __init__(self, base_url = "http://simplesage_roed.appspot.com/", worker_subdir = "worker/", \
                       delay = 0.02, checkup_interval = 0.01):
        self.base_url = base_url
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
            print type(msg), msg
            msg = json.loads(msg)
            cmd, userid, data = msg['cmd'], msg['userid'], msg['data']
            print "Handling %s command"%(cmd)
            self.handle_command(cmd, userid, data)

    def handle_command(self, cmd, userid, data):
        if cmd == 'exec':
            self.exec_code(userid, data)
        elif cmd == 'kill':
            assert False
            self.kill_session(userid)

    def exec_code(self, userid, data):
        session = self.sessions.get(userid, self.fork_new_session(userid))
        cellid, code = data['cellid'], data['code']
        code = preparse(code)
        session.execute(cellid, code)

    def fork_new_session(self, userid):
        new_session = SageSession(self, userid, self.delay, self.checkup_interval)
        self.sessions[userid] = new_session
        return new_session

    def post(self, userid, cellid, out, status):
        if DEBUG:
            print "POSTING: %s, %s, %s, %s"%(userid, cellid, out, status)
        else:
            url = self.base_url + "worker/update"
            data = urllib.urlencode({'userid':userid, 'cellid':cellid, 'output':out, 'status':status})
            urllib2.urlopen(url, data=data)
        
class SageSession(object):
    def __init__(self, worker, userid, delay, checkup_interval = 0.01):
        self.worker = worker
        self.userid = userid
        from sagenb.interfaces.expect import WorksheetProcess_ExpectImplementation
        self.expect = WorksheetProcess_ExpectImplementation()
        self.expect.execute("from sage.all import *\n")
        self.exec_queue = []
        self.checkup_interval = checkup_interval
        self.set_starting_intervals()
        self.cur_cellid = None
        self.output_len = 0

    def set_starting_intervals(self):
        self.post_interval = self.checkup_interval
        self.worker.checkup_times[self.userid] = self.next_post = time.time() + self.checkup_interval

    def clear_intervals(self):
        del self.worker.checkup_times[self.userid]

    def execute(self, cellid, code):
        self.exec_queue.append((cellid, code))
        self.query_status() # starts execution if there's nothing in the exec_queue

    def _execute(self):
        self.cur_cellid, code = self.exec_queue.pop(0)
        self.expect.execute(code)
        self.output_len = 0
        self.set_starting_intervals()

    def query_status(self):
        status = self.expect.output_status()
        new_out = status.output[self.output_len:].strip()
        cur_cellid = self.cur_cellid
        if status.done:
            if len(self.exec_queue) > 0:
                self._execute()
            else:
                self.clear_intervals()
            if cur_cellid is not None: # cur_cellid is None for the initial import
                self.worker.post(self.userid, cur_cellid, new_out, 'done')
        elif new_out and time.time() > self.next_post:
            self.output_len = len(status.output)
            self.worker.post(self.userid, cur_cellid, new_out, 'working')
            if self.post_interval < self.checkup_interval * 32:
                self.post_interval *= 2
            self.next_post = time.time() + self.post_interval

    def new_output(self, status):
        new_out = status.output[self.output_len:]
        self.output_len = len(status.output)
        return new_out
            

if __name__ ==  '__main__':
    SageGAEWorker()
