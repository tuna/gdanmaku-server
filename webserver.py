#!/usr/bin/env python2
# -*- coding:utf-8 -*-

import json
from flask import Flask, request, render_template
import gevent
from gevent.wsgi import WSGIServer

app = Flask("Danmaku")

new_danmaku = gevent.event.Event()
danmaku_channels = {
    "default": []
}


@app.route("/", methods=["GET"])
def index():
    channel = request.args.get("c", "default")
    if channel not in danmaku_channels:
        danmaku_channels[channel] = []

    return render_template("index.html", channel=channel)


@app.route("/danmaku/stream", methods=["GET"])
def danmaku_stream():
    channel = request.args.get("c", "default")
    if channel not in danmaku_channels:
        danmaku_channels[channel] = []

    if new_danmaku.wait(timeout=5):
        r = json.dumps(danmaku_channels[channel])
        danmaku_channels[channel] = []
        new_danmaku.clear()
        return r
    else:
        return json.dumps(danmaku_channels[channel])


@app.route("/danmaku/", methods=["POST"])
def publish_danmaku():
    channel = request.args.get("c", "default")
    if channel not in danmaku_channels:
        danmaku_channels[channel] = []

    if request.json:
        danmaku = {
            "text": request.json["content"],
            "style": request.json.get("color", "white"),
            "position": request.json.get("position", "fly")
        }
    else:
        danmaku = {
            "text": request.form["content"],
            "style": request.form.get("style", "white"),
            "position": request.form.get("position", "fly")
        }

    # interface.new_danmaku(content)
    danmaku_channels[channel].append(danmaku)
    new_danmaku.set()
    return "OK"


if __name__ == "__main__":
    http_server = WSGIServer(('', 5000), app)
    http_server.serve_forever()


# vim: ts=4 sw=4 sts=4 expandtab
