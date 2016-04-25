#!/usr/bin/env python2
# -*- coding:utf-8 -*-
from gevent.monkey import patch_all
patch_all()

import redis
from gevent.wsgi import WSGIServer
from flask import Flask, g, request, session
from flask.ext.babel import Babel

from . import settings
from .channel_manager import ChannelManager

app = Flask(__name__)
app.config.from_object(settings)
r = redis.StrictRedis(
    host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB)
chan_mgr = ChannelManager(app, r)

babel = Babel(app)

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


@babel.localeselector
def get_locale():
    language = request.args.get(
        "lang",
        session.get(
            "language",
            request.accept_languages.best_match(['zh', 'en']),
        ),
    )
    session["language"] = language
    return language

from . import views
from . import api
from . import wechat

def main():
    http_server = WSGIServer(('', 5000), app)
    print("Serving at 0.0.0.0:5000")
    http_server.serve_forever()


# vim: ts=4 sw=4 sts=4 expandtab
