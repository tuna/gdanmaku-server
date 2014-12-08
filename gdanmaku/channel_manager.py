#!/usr/bin/env python2
# -*- coding:utf-8 -*-
import json
import redis
import gevent
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app, g


class Subscriber(object):
    SUBSCRIBER_PREFIX = "subscriber_"

    @classmethod
    def exists(cls, cname, sub_id):
        return g.r.exists(cls.prefix(cname) + sub_id)

    @classmethod
    def create(cls, cname, sub_id, ttl=10):
        key = cls.prefix(cname) + sub_id
        g.r.setex(key, ttl, "{}:{}".format(sub_id, ttl))

    @classmethod
    def refresh(cls, cname, sub_id):
        key = cls.prefix(cname) + sub_id
        ttl = int(g.r.get(key).split(":")[1])
        g.r.expire(key, ttl)
        bkey = cls.buffer(cname, sub_id)
        if g.r.exists(bkey):
            g.r.expire(bkey, ttl)

    @classmethod
    def prefix(cls, cname):
        return current_app.config.get("REDIS_PREFIX") \
            + cls.SUBSCRIBER_PREFIX + cname + "_chan_"

    @classmethod
    def buffer(cls, cname, sub_id):
        return current_app.config.get("REDIS_PREFIX") \
            + cls.SUBSCRIBER_PREFIX + cname + "_buffer_" + sub_id


class Channel(object):

    CHANNEL_PREFIX = "chan_"

    @classmethod
    def prefix(cls):
        return current_app.config.get("REDIS_PREFIX") + cls.CHANNEL_PREFIX

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
        return [(g.r.get(k), k) for k in g.r.keys(Subscriber.prefix(self.name)+"*")]

    @staticmethod
    def from_json(jstr):
        dchan = json.loads(jstr)
        if 'name' not in dchan:
            return None

        name = dchan['name']
        desc = dchan.get('desc', 'Test')
        sub_passwd = dchan.get('sub_passwd', "")
        pub_passwd = dchan.get('pub_passwd', None)
        c = Channel(name, desc)
        c.sub_passwd = sub_passwd
        c.pub_passwd = pub_passwd
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
        retry = []
        for st, c in self.subscribers:
            sname, _ = st.split(":")
            bname = Subscriber.buffer(self.name, sname)
            g.r.rpush(bname, json.dumps(danmaku))
            if g.r.ttl(bname) < 0:
                g.r.expire(bname, g.r.ttl(c))
            if g.r.llen(bname) > 20:
                g.r.ltrim(bname, -1, -10)

            n = g.r.publish(c, 1)
            if n < 1:
                retry.append(c)

        if len(retry) > 0:
            gevent.sleep(0.2)
            for c in retry:
                g.r.publish(c, 1)

    def pop_danmakus(self, sname):

        if Subscriber.exists(self.name, sname):
            Subscriber.refresh(self.name, sname)
        else:
            Subscriber.create(self.name, sname)

        bname = Subscriber.buffer(self.name, sname)
        if g.r.exists(bname):
            msg = g.r.lrange(bname, 0, -1)
            g.r.delete(bname)
            return map(lambda x: json.loads(x), msg)

        chan = Subscriber.prefix(self.name) + sname
        p = g.r.pubsub()
        p.subscribe(chan)
        try:
            for msg in p.listen():
                if msg['type'] == "message":
                    return [json.loads(g.r.lpop(bname)), ]
        except redis.TimeoutError:
            return []


class ChannelManager(object):

    def __init__(self, app, r):
        self.app = app
        self.r = r   # redis client

    def channels(self, instance=False):
        keys = self.r.keys(Channel.prefix()+"*")
        return [Channel.from_json(self.r.get(k)) for k in keys] \
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
        return Channel.from_json(self.r.get(key) or "{}")


# vim: ts=4 sw=4 sts=4 expandtab
