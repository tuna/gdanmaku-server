#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import json
import binascii
import os
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
            + cls.SUBSCRIBER_PREFIX + cname + "_meta_"

    @classmethod
    def buffer(cls, cname, sub_id):
        return current_app.config.get("REDIS_PREFIX") \
            + cls.SUBSCRIBER_PREFIX + cname + "_buffer_" + sub_id


class Token(object):

    TOKEN_PREFIX = "token_"

    @classmethod
    def new(cls, chan, rate=0):
        token = binascii.hexlify(os.urandom(8)).decode()
        key = cls.TOKEN_PREFIX + token
        val = {'c': chan.name, 'r': rate}
        ttl = chan.ttl()
        if ttl < 0:
            ttl = 3600
        g.r.setex(key, ttl, json.dumps(val))
        return token

    @classmethod
    def verify(cls, chan, token):
        key = cls.TOKEN_PREFIX + token
        jv, _ = (g.r.pipeline()
                 .get(key)
                 .delete(key)
                 .execute())

        if jv is None:
            return False

        val = json.loads(jv)
        return val['c'] == chan.name


class Channel(object):

    CHANNEL_PREFIX = "chan_"

    @classmethod
    def prefix(cls):
        return current_app.config.get("REDIS_PREFIX") + cls.CHANNEL_PREFIX

    def __init__(self, name, desc="Test", ttl=-1, sub_passwd="",
                 pub_passwd=None, exam_passwd=None):
        self.name = name
        self.desc = desc
        self._ttl = ttl
        self.sub_passwd = generate_password_hash(sub_passwd)
        self.pub_passwd = generate_password_hash(pub_passwd) \
            if pub_passwd else None
        self.exam_passwd = generate_password_hash(exam_passwd) \
            if exam_passwd else None


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
        exam_passwd = dchan.get('exam_passwd', None)
        c = Channel(name, desc, ttl=None)
        c.sub_passwd = sub_passwd
        c.pub_passwd = pub_passwd
        c.exam_passwd = exam_passwd
        return c

    def ttl(self):
        if self._ttl is None:
            return g.r.ttl(self.key)
        elif self._ttl < 0:
            return self._ttl
        else:
            return self._ttl * 60 * 60

    def to_dict(self, public=False):
        if public:
            return {
                'name': self.name,
                'desc': self.desc,
                'is_open': self.is_open,
                'need_exam': self.need_exam,
                'ttl': self.ttl()
            }
        else:
            return {
                'name': self.name,
                'desc': self.desc,
                'sub_passwd': self.sub_passwd,
                'pub_passwd': self.pub_passwd,
                'exam_passwd': self.exam_passwd,
                'ttl': self.ttl()
            }

    def to_json(self):
        return json.dumps(self.to_dict())

    @property
    def is_open(self):
        return self.pub_passwd is None

    @property
    def need_exam(self):
        return self.exam_passwd is not None

    def verify_sub_passwd(self, password):
        return check_password_hash(self.sub_passwd, password)

    def verify_pub_passwd(self, password):
        if self.pub_passwd is None:
            return True
        return check_password_hash(self.pub_passwd, password)

    def verify_exam_passwd(self, password):
        if self.exam_passwd is None:
            return True
        return check_password_hash(self.exam_passwd, password)

    def gen_web_token(self):
        return Token.new(self)

    def verify_token(self, token):
        # TODO: rate limited tokens
        return Token.verify(self, token)

    def new_danmaku(self, danmaku):
        for st, c in self.subscribers:
            sname, _ = st.split(":")
            bname = Subscriber.buffer(self.name, sname)
            if g.r.ttl(bname) < 0:
                g.r.expire(bname, g.r.ttl(c))
            if g.r.llen(bname) > 20:
                g.r.ltrim(bname, -1, -10)
            g.r.rpush(bname, json.dumps(danmaku))

    def pop_danmakus(self, sname):

        if Subscriber.exists(self.name, sname):
            Subscriber.refresh(self.name, sname)
        else:
            Subscriber.create(self.name, sname)

        bname = Subscriber.buffer(self.name, sname)
        if g.r.exists(bname):
            msg = g.r.lrange(bname, 0, -1)
            g.r.delete(bname)
            return [json.loads(x) for x in msg]

        ret = g.r.blpop(bname, timeout=5)
        if ret is None:
            return []

        _, msg = ret
        return [json.loads(msg), ]

    def new_danmaku_exam(self, danmaku):
        bname = self.prefix() + self.name + "_exam"
        g.r.rpush(bname, json.dumps(danmaku))
        g.r.expire(bname, self.ttl())

    def pop_exam_danmakus(self):
        msgs = []
        bname = self.prefix() + self.name + "_exam"

        # many agents may be examining danakus at the same time
        # so atomic popping is needed
        def pop_dm_transaction(pipe):
            jmsgs = pipe.lrange(bname, 0, -1)
            pipe.delete(bname)
            pipe.multi()
            for m in jmsgs:
                msgs.append(json.loads(m))

        if g.r.exists(bname):
            g.r.transaction(pop_dm_transaction, bname)
            return msgs

        ret = g.r.blpop(bname, timeout=5)
        if ret is None:
            return []

        _, msg = ret
        return [json.loads(msg), ]


class ChannelManager(object):

    def __init__(self, app, r):
        self.app = app
        self.r = r   # redis client

    def channels(self, instance=False):
        def _chan_generator(keys, inst):
            C = (lambda x: Channel.from_json(x)) if inst else (lambda x: x)
            for k in keys:
                try:
                    v = self.r.get(k)
                except:
                    self.r.delete(k)
                else:
                    yield C(v)

        keys = self.r.keys(Channel.prefix()+"*")
        return list(_chan_generator(keys, instance))

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
