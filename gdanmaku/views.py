#!/usr/bin/env python2
# -*- coding:utf-8 -*-
from flask import render_template
from flask import request, g, session
import gevent

from . import app

new_danmaku = gevent.event.Event()
danmaku_channels = {
    "default": []
}


@app.route("/channel/<cname>", methods=["GET"])
def channel_view(cname):
    cm = g.channel_manager
    passwd = request.args.get("pw", "")
    channel = cm.get_channel(cname)
    if channel is None:
        return "Not Found", 404

    token = channel.gen_web_token()

    return render_template(
        "channel.html", channel=channel,
        token=token, passwd=passwd)


@app.route("/channel/<cname>/examination", methods=["GET"])
def channel_examination_view(cname):
    cm = g.channel_manager
    language = request.args.get("lang", session.get("language", "zh_CN"))
    session["language"] = language
    passwd = request.args.get("pw", "")
    channel = cm.get_channel(cname)
    if channel is None:
        return "Not Found", 404

    token = channel.gen_web_token()

    return render_template(
        "channel_exam.html", channel=channel,
        token=token, passwd=passwd,
        language=language)


@app.route("/", methods=["GET"])
def index():
    language = request.args.get("lang", session.get("language", "zh_CN"))
    session["language"] = language
    channels = g.channel_manager.channels(instance=True)
    return render_template(
        "index.html", channels=channels, language=language)


@app.route("/channel-new/", methods=["GET"])
def channel_create():
    language = request.args.get("lang", session.get("language", "zh_CN"))
    session["language"] = language
    return render_template("new_channel.html", language=language)

# vim: ts=4 sw=4 sts=4 expandtab
