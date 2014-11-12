#!/usr/bin/env python2
# -*- coding:utf-8 -*-
import gevent
import gevent.lock
import gevent.queue
import Queue

from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash


class Subscriber(object):

    def __init__(self, name="ALL", timeout=15):
        self.name = name
        self.last_seen = datetime.now()
        self.timeout = timeout
        self.queue = gevent.queue.Queue()

    def refresh(self):
        self.last_seen = datetime.now()

    def exceeded(self):
        if self.name == "ALL":
            return False

        return datetime.now() - self.last_seen > timedelta(seconds=self.timeout)

    def clear_queue(self):
        if self.queue.qsize() >= 100:
            for _ in range(80):
                try:
                    self.queu.get_nowait()
                except Queue.Empty:
                    return


class Channel(object):

    def __init__(self, name, desc="Test", timeout=5, ttl=-1,
                 sub_passwd="", pub_passwd=None):
        self.name = name
        self.desc = desc
        self.timeout = timeout
        self.gc_time = datetime.now() + timedelta(hours=ttl) \
            if ttl > 0 else None

        self.sub_passwd = generate_password_hash(sub_passwd)
        self.pub_passwd = generate_password_hash(pub_passwd) \
            if pub_passwd else None

        self.subscribers = {"ALL": Subscriber("ALL")}
        self.lock = gevent.lock.RLock()

    @property
    def is_open(self):
        return self.pub_passwd is None

    def verify_sub_passwd(self, password):
        return check_password_hash(self.sub_passwd, password)

    def verify_pub_passwd(self, password):
        if self.pub_passwd is None:
            return True
        return check_password_hash(self.pub_passwd, password)

    def new_danmaku(self, danmaku):
        self.lock.acquire()
        self._subscriber_gc()
        for _, s in self.subscribers.iteritems():
            s.queue.put(danmaku)
        self.lock.release()

    def pop_danmakus(self, sname):
        self.lock.acquire()
        s = self.subscribers.get(sname, None)
        if s is None:
            s = Subscriber(sname)
            self.subscribers[sname] = s
        else:
            s.refresh()
        self.lock.release()

        buflen = s.queue.qsize()
        if buflen > 0:
            return [s.queue.get_nowait() for _ in range(buflen)]
        else:
            try:
                msg = s.queue.get(timeout=self.timeout)
                return [msg, ]
            except Queue.Empty:
                return []

    def subscriber_gc(self):
        self.lock.acquire()
        self._subscriber_gc()
        self.lock.release()

    def _subscriber_gc(self):
        self.subscribers = \
            {k: s for k, s in self.subscribers.iteritems() if not s.exceeded()}
        s = self.subscribers["ALL"]
        s.clear_queue()


class ChannelManager(object):

    def __init__(self, app):
        self.channels = {}   # name: object
        self.app = app
        gevent.spawn(self.garbage_collector)

    def new_channel(self, name, **kwargs):
        channel = Channel(name, **kwargs)
        if name in self.channels:
            return None

        self.channels[name] = channel
        return True

    def get_channel(self, name):
        return self.channels.get(name, None)

    def garbage_collector(self):
        print("Starting channel GC")
        while 1:
            _buf = [(k, v) for k, v in self.channels.items()]
            for cname, chan in _buf:
                if chan.gc_time is None:
                    continue
                if datetime.now() > chan.gc_time:
                    self.channels.pop(cname)

            _buf = [(k, v) for k, v in self.channels.items()]
            for _, chan in _buf:
                chan.subscriber_gc()

            gevent.sleep(10*60)

# vim: ts=4 sw=4 sts=4 expandtab
