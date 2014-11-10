#!/usr/bin/env python2
# -*- coding:utf-8 -*-
import json
from flask import request, g
from . import app


@app.route("/api/v1/channels", methods=["GET"])
def api_list_channels():
    pass


@app.route("/api/v1/channels", methods=["POST"])
def api_create_channel():
    form = request.json if request.json else request.form

    try:
        kwargs = {
            "name": form["name"],
            "desc": form["desc"],
            "ttl": int(form.get("ttl", 2)),
            "sub_passwd": form["sub_passwd"],
            "pub_passwd": form.get("pub_passwd", ""),
        }
    except:
        return "Invalid Request", 400

    if g.channel_manager.new_channel(**kwargs) is None:
        return "Channel Existed", 409

    return json.dumps({"url": "/channel/{}".format(form["name"])})


@app.route("/api/v1/channels/<cname>", methods=["GET"])
def api_channel_page(cname):
    pass


@app.route("/api/v1/channels/<cname>/danmaku", methods=["POST"])
def api_post_danmaku(cname):
    cm = g.channel_manager

    channel = cm.get_channel(cname)
    if channel is None:
        return "Not Found", 404

    if not channel.is_open:
        key = request.headers.get("X-GDANMAKU-AUTH-KEY")
        if key is None or (not channel.verify_pub_passwd(key)):
            return "Forbidden", 403

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
    channel.new_danmaku(danmaku)
    return "OK"


@app.route("/api/v1/channels/<cname>/danmaku", methods=["GET"])
def api_channel_danmaku(cname):
    cm = g.channel_manager

    channel = cm.get_channel(cname)
    if channel is None:
        return "Not Found", 404

    key = request.headers.get("X-GDANMAKU-AUTH-KEY")
    if key is None or (not channel.verify_sub_passwd(key)):
        return "Forbidden", 403

    r = channel.pop_danmakus("ALL")
    return json.dumps(r)


@app.route("/api/v1.1/channels/<cname>/danmaku", methods=["GET"])
def api_channel_danmaku_1(cname):
    cm = g.channel_manager

    channel = cm.get_channel(cname)
    if channel is None:
        return "Not Found", 404

    sname = request.headers.get("X-GDANMAKU-SUBSCRIBER-ID", "ALL")
    key = request.headers.get("X-GDANMAKU-AUTH-KEY")
    if key is None or (not channel.verify_sub_passwd(key)):
        return "Forbidden", 403

    r = channel.pop_danmakus(sname)
    return json.dumps(r)


# vim: ts=4 sw=4 sts=4 expandtab
