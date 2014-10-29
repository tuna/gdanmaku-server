#!/usr/bin/env python2
# -*- coding:utf-8 -*-
import gevent
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash


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

        self.ev_new = gevent.event.Event()
        self.danmaku_buffer = []

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
        self.danmaku_buffer.append(danmaku)
        self.ev_new.set()

    def pop_danmakus(self):
        if self.ev_new.wait(timeout=self.timeout):
            buf = self.danmaku_buffer
            self.danmaku_buffer = []
            self.ev_new.clear()
            return buf
        else:
            return []


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
            _buf = self.channels.items()
            for cname, chan in _buf:
                if chan.gc_time is None:
                    continue
                if datetime.now() > chan.gc_time:
                    self.channels.pop(cname)

            gevent.sleep(10*60)

# vim: ts=4 sw=4 sts=4 expandtab
