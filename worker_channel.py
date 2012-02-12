#!/usr/bin/env python
import json, time, urllib, urllib2, sys, logging, socket, os
import gae_channel
import multiprocessing
from Queue import Empty

#import sage.all_cmdline

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
        return self

    def next(self):
        if self.checking:
            for userid, t in self.worker.checkup_times.iteritems():
                curtime = time.time()
                if curtime >= t:
                    self.worker.check(userid)
            self.checking = False
        try:
            try:
                msg = self.lpm.next()
                self._backoff = 1
                self._need_reconnect = False
            except StopIteration:
                self.lpm = self.chan.long_poll_messages()
                try:
                    msg = self.lpm.next()
                    self._backoff = 1
                    self._need_reconnect = False
                except StopIteration:
                    # No messages right now.
                    self.wait()
                    self.checking = True
                    return self.next()
        except gae_channel._TalkMessageCorrupted, e:
            self.chan.logger.warn('TalkMessageCorrupted: %s' % str(e))
            self.chan.logger.warn('reconnecting')
            return self.next()
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
            return self.next()
        return msg

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
                       delay = 0.02, base_checkup_interval = 0.01):
        self.base_url = base_url
        self.worker_subdir = worker_subdir
        self.delay = delay
        self.base_checkup_interval = base_checkup_interval
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
            #sys.stderr.write("Handling %s command"%(cmd))
            #sys.stderr.flush()
            print "Handling %s command"%(cmd)
            self.handle_command(cmd, userid, data)

    def check(self, userid):
        session = self.sessions[userid]
        if session.process.is_alive():
            results = []
            base_tell = session.last_tell
            while True:
                try:
                    results.append(session.done.get_nowait() + ("done",))
                    session.active_commands -= 1
                    session.checkup_interval = session.base_checkup_interval
                except Empty:
                    break
            newest_tell = results[-1][1] if len(results) > 0 else base_tell
            cur_tell = session.output.tell()
            if session.output.tell() > newest_tell:
                assert session.active_commands > 0
                results.append((cellid, cur_tell, "working"))
                if session.checkup_interval < session.base_checkup_interval * 128:
                    session.checkup_interval *= 2
            if session.active_commands > 0:
                self.worker.checkup_times[userid] = time.time() + session.checkup_interval
            session.output.seek(base_tell)
            for cellid, new_tell, status in results:
                out = session.output.read(new_tell - base_tell)
                self.post(userid, cellid, out, status)
                base_tell = new_tell
            session.last_tell = base_tell

    def handle_command(self, cmd, userid, data):
        if cmd == 'exec':
            self.exec_code(userid, data)
        elif cmd == 'kill':
            assert False
            self.kill_session(userid)

    def exec_code(self, userid, data):
        print data
        session = self.sessions.get(userid, self.fork_new_session(userid))
        session.input.put(data)
        session.active_commands += 1
        self.checkup_times[userid] = time.time() + self.base_checkup_interval

    def fork_new_session(self, userid):
        print "FORKING"
        sys.stdout.flush()
        new_session = SageSession(self.delay, self.base_checkup_interval)
        self.sessions[userid] = new_session
        new_session.process.start()
        return new_session

    def post(self, userid, cellid, out, status):
        print "POSTING: %s, %s, %s, %s"%(userid, cellid, out, status)
        #url = self.base_url + "worker/update"
        #data = urllib.urlencode({'userid':userid, 'cellid':cellid, 'output':out, 'status':status})
        #urllib2.urlopen(url, data=data)

class SageSession(object):
    def __init__(self, delay, base_checkup_interval = 0.01):
        self.output = os.tmpfile()
        print "opening input"
        sys.stdout.flush()
        self.input = multiprocessing.Queue()
        print "opening done"
        sys.stdout.flush()
        self.done = multiprocessing.Queue()
        self.process = SageProcess(self.input, self.done, self.output, delay)
        self.last_tell = 0
        self.active_commands = 0
        self.base_checkup_interval = base_checkup_interval
        self.checkup_interval = base_checkup_interval

class SageProcess(multiprocessing.Process):
    def __init__(self, input_queue, done_queue, output_file, delay):
        multiprocessing.Process.__init__(self)
        self.input_queue = input_queue
        self.done_queue = done_queue
        self.output_file = output_file
        self.delay = delay
        self.globs = {}
        #for ky, val in sage.all.__dict__.iteritems():
        #    self.globs[ky] = val
        os.dup2(output_file.fileno(), sys.stdout.fileno())

    def run(self):
        while True:
            try:
                data = self.input_queue.get_nowait()
                cellid, code = data['cellid'], data['code']
            except Empty:
                time.sleep(self.delay)
                continue
            sys.stderr.write("hello " + code)
            sys.stderr.flush()
            exec code in {}
            print "bbye"
            self.done_queue.put((cellid,self.output_file.tell()))
        
if __name__ ==  '__main__':
    SageGAEWorker()

# preparse
