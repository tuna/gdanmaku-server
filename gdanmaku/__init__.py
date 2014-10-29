#!/usr/bin/env python2
# -*- coding:utf-8 -*-
from flask import Flask, g
from gevent.wsgi import WSGIServer
from . import settings
from .channel_manager import ChannelManager

app = Flask(__name__)
app.config.from_object(settings)
chan_mgr = ChannelManager(app)
chan_mgr.new_channel("demo", desc=u"演示频道, 发布、订阅均无需密码")


@app.before_request
def set_channel_manager():
    g.channel_manager = chan_mgr


from . import views
from . import api


def main():
    app.debug = True
    http_server = WSGIServer(('', 5000), app)
    print("Serving at 0.0.0.0:5000")
    http_server.serve_forever()


# vim: ts=4 sw=4 sts=4 expandtab
