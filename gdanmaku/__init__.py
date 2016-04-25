#!/usr/bin/env python2
# -*- coding:utf-8 -*-
from gevent.monkey import patch_all
patch_all()

import redis
from gevent.wsgi import WSGIServer
from flask import Flask, g
from . import settings
from .channel_manager import ChannelManager

app = Flask(__name__)
app.config.from_object(settings)
r = redis.StrictRedis(
    host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB)
chan_mgr = ChannelManager(app, r)

with app.app_context():
    for kwargs in app.config.get("PERSISTENT_CHANNELS", []):
        chan_mgr.new_channel(**kwargs)


@app.before_request
def set_channel_manager():
    g.channel_manager = chan_mgr
    try:
        r.ping()
    except:
        r.connection_pool.reset()
    g.r = r


from . import views
from . import api
from . import wechat


def main():
    app.debug = True
    http_server = WSGIServer(('', 5000), app)
    print("Serving at 0.0.0.0:5000")
    http_server.serve_forever()


# vim: ts=4 sw=4 sts=4 expandtab
