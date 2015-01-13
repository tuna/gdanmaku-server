#!/usr/bin/env python2
# -*- coding:utf-8 -*-
import json
# import redis
from werkzeug.security import generate_password_hash, check_password_hash
# from flask import current_app


class Subscriber(object):
    SUBSCRIBER_PREFIX = "subscriber_"

    @classmethod
    def exists(cls, r, cname, sub_id):
        return r.exists(cls.prefix(cname) + sub_id)

    @classmethod
    def create(cls, r, cname, sub_id, ttl=10):
        key = cls.prefix(cname) + sub_id
        r.setex(key, ttl, "{}:{}".format(sub_id, ttl))

    @classmethod
    def refresh(cls, r, cname, sub_id):
        key = cls.prefix(cname) + sub_id
        ttl = int(r.get(key).split(":")[1])
        r.expire(key, ttl)
        bkey = cls.buffer(cname, sub_id)
        if r.exists(bkey):
            r.expire(bkey, ttl)

    @classmethod
    def prefix(cls, cname):
        return ChannelManager.REDIS_PREFIX \
            + cls.SUBSCRIBER_PREFIX + cname + "_meta_"

    @classmethod
    def buffer(cls, cname, sub_id):
        return ChannelManager.REDIS_PREFIX \
            + cls.SUBSCRIBER_PREFIX + cname + "_buffer_" + sub_id


class Channel(object):

    CHANNEL_PREFIX = "chan_"

    @classmethod
    def prefix(cls):
        return ChannelManager.REDIS_PREFIX + cls.CHANNEL_PREFIX

    def __init__(self, name, desc="Test", ttl=-1, sub_passwd="", pub_passwd=None):
        self.name = name
        self.desc = desc
        self._ttl = ttl
        self.sub_passwd = generate_password_hash(sub_passwd)
        self.pub_passwd = generate_password_hash(pub_passwd) \
            if pub_passwd else None

    @property
    def key(self):
        return self.prefix() + self.name

    @property
    def subscribers(self):
        return [(self.r.get(k), k)
                for k in self.r.keys(Subscriber.prefix(self.name)+"*")]

    @staticmethod
    def from_json(jstr, manager):
        dchan = json.loads(jstr)
        if 'name' not in dchan:
            return None

        name = dchan['name']
        desc = dchan.get('desc', 'Test')
        ttl = dchan.get('_ttl', -1)
        sub_passwd = dchan.get('sub_passwd', "")
        pub_passwd = dchan.get('pub_passwd', None)
        c = Channel(name, desc, ttl)
        c.sub_passwd = sub_passwd
        c.pub_passwd = pub_passwd
        c.m = manager
        c.r = manager.r
        return c

    def to_dict(self, public=False):
        if public:
            return {
                'name': self.name,
                'desc': self.desc,
            }
        else:
            return {
                'name': self.name,
                'desc': self.desc,
                'sub_passwd': self.sub_passwd,
                'pub_passwd': self.pub_passwd,
            }

    def to_json(self):
        return json.dumps(self.to_dict())

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
        for st, c in self.subscribers:
            sname, _ = st.split(":")
            bname = Subscriber.buffer(self.name, sname)
            if self.r.ttl(bname) < 0:
                self.r.expire(bname, self.r.ttl(c))
            if self.r.llen(bname) > 20:
                self.r.ltrim(bname, -1, -10)
            self.r.rpush(bname, json.dumps(danmaku))

    def pop_danmakus(self, sname):

        if Subscriber.exists(self.r, self.name, sname):
            Subscriber.refresh(self.r, self.name, sname)
        else:
            Subscriber.create(self.r, self.name, sname)

        bname = Subscriber.buffer(self.name, sname)
        if self.r.exists(bname):
            msg = self.r.lrange(bname, 0, -1)
            self.r.delete(bname)
            return map(lambda x: json.loads(x), msg)

        ret = self.r.blpop(bname, timeout=5)
        if ret is None:
            return []

        _, msg = ret
        return [json.loads(msg), ]

        # try:
        #     _, msg = g.r.blpop(bname, timeout=5)
        # except redis.TimeoutError:
        #     return []
        # else:
        #     return [json.loads(msg), ]


class ChannelManager(object):

    REDIS_PREFIX = None

    def __init__(self, app, r):
        self.app = app
        self.r = r   # redis client
        ChannelManager.REDIS_PREFIX = app.config.get("REDIS_PREFIX")

    def channels(self, instance=False):
        keys = self.r.keys(Channel.prefix()+"*")
        return [Channel.from_json(self.r.get(k), self) for k in keys] \
            if instance else [self.r.get(k) for k in keys]

    def new_channel(self, name, **kwargs):
        key = Channel.prefix() + name
        if self.r.exists(key):
            return None

        channel = Channel(name, **kwargs)
        self.r.set(key, channel.to_json())
        if channel._ttl > 0:
            self.r.expire(key, channel._ttl * 60 * 60)
        return True

    def get_channel(self, name):
        key = Channel.prefix() + name
        return Channel.from_json(self.r.get(key) or "{}", self)


# vim: ts=4 sw=4 sts=4 expandtab
