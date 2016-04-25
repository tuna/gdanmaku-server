#!/usr/bin/env python2
# -*- coding:utf-8 -*-
import json
from flask import request, g, Response
import gevent
from . import app
from .shared import RE_INVALID, DM_COLORS, DM_POSITIONS


def jsonResponse(r):
    res = Response(json.dumps(r), mimetype='application/json')
    res.headers.add('Access-Control-Allow-Origin', '*')
    res.headers.add(
        'Access-Control-Allow-Headers',
        'Content-Type,X-GDANMAKU-AUTH-KEY,X-GDANMAKU-SUBSCRIBER-ID')
    res.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    return res


@app.route("/api/v1/channels", methods=["GET"])
def api_list_channels():
    channels = g.channel_manager.channels(instance=True)
    return jsonResponse({'channels': [c.to_dict(public=True) for c in channels]})


@app.route("/api/v1/channels", methods=["POST"])
def api_create_channel():
    form = request.json if request.json else request.form

    try:
        kwargs = {
            "name": form["name"],
            "desc": form["desc"],
            "ttl": int(form.get("ttl", 2)),
            "sub_passwd": form["sub_passwd"],
            "pub_passwd": form.get("pub_passwd", None),
            "exam_passwd": form.get("exam_passwd", None),
        }
    except:
        return "Invalid Request", 400

    if g.channel_manager.new_channel(**kwargs) is None:
        return "Channel Existed", 409

    return jsonResponse({"url": "/channel/{}".format(form["name"])})


@app.route("/api/v1/channels/<cname>", methods=["GET"])
def api_channel_page(cname):
    pass


# OPTIONS response to enable cross-site subscription
@app.route("/api/v1/channels/<cname>/danmaku", methods=["OPTIONS"])
@app.route("/api/v1.1/channels/<cname>/danmaku", methods=["OPTIONS"])
def api_channel_options(cname):
    return jsonResponse({"status": "OK"})


# Post danmaku
@app.route("/api/v1/channels/<cname>/danmaku", methods=["POST"])
def api_post_danmaku(cname):
    cm = g.channel_manager
    form = request.json if request.json else request.form

    channel = cm.get_channel(cname)
    if channel is None:
        return "Not Found", 404

    if not channel.is_open:
        key = request.headers.get("X-GDANMAKU-AUTH-KEY")
        if key is None or (not channel.verify_pub_passwd(key)):
            return "Forbidden", 403

    valid_exam_client = False
    if channel.need_exam:
        exam_key = request.headers.get("X-GDANMAKU-EXAM-KEY", None)
        if exam_key is not None:
            if not channel.verify_exam_passwd(exam_key):
                return "Bad Exam Password", 403
            valid_exam_client = True

    res = {}

    # if this is to exam, no need to limit rate
    if not valid_exam_client:
        _token = request.headers.get("X-GDANMAKU-TOKEN")
        if _token is None:
            return "Token is required", 400

        try:
            ttype, token = _token.split(':')
        except ValueError:
            return "Bad Request", 400

        if ttype == "WEB":
            if not channel.verify_token(token):
                return "Invalid Token, lost synchronization", 428
            res['token'] = channel.gen_web_token()
        elif ttype == "APP":
            # TODO: Implement
            pass
        else:
            return "Bad Request", 400

    try:
        content = form['content']
    except KeyError:
        return "Bad Request", 400

    if (RE_INVALID.search(content) or
            (len(content.strip()) < 1) or
            (len(content.strip()) > 128)):
        return "Bad Request", 400

    style = form.get("color", "blue")
    if style not in DM_COLORS:
        style = "blue"
    position = form.get("position", "fly")
    if position not in DM_POSITIONS:
        position = "fly"

    danmaku = {
        "text": content,
        "style": style,
        "position": position
    }

    if not channel.need_exam:
        channel.new_danmaku(danmaku)
    else:
        if valid_exam_client:
            # gevent.sleep(1)
            channel.new_danmaku(danmaku)
        else:
            channel.new_danmaku_exam(danmaku)

    res['ret'] = "OK"
    return jsonResponse(res)


@app.route("/api/v1/channels/<cname>/danmaku", methods=["GET"])
@app.route("/api/v1.1/channels/<cname>/danmaku", methods=["GET"])
def api_channel_danmaku(cname):
    cm = g.channel_manager

    channel = cm.get_channel(cname)
    if channel is None:
        return "Not Found", 404

    sname = request.headers.get("X-GDANMAKU-SUBSCRIBER-ID", "ALL")
    key = request.headers.get("X-GDANMAKU-AUTH-KEY", "")
    if not channel.verify_sub_passwd(key):
        return "Forbidden", 403

    r = channel.pop_danmakus(sname)
    return jsonResponse(r)


@app.route("/api/v1/channels/<cname>/danmaku/exam", methods=["GET"])
def api_danmaku_to_exam(cname):
    cm = g.channel_manager

    channel = cm.get_channel(cname)
    if channel is None:
        return "Not Found", 404

    key = request.headers.get("X-GDANMAKU-EXAM-KEY", "")
    if not channel.verify_exam_passwd(key):
        return "Forbidden", 403

    r = channel.pop_exam_danmakus()
    return jsonResponse(r)


__all__ = ['api_channel_danmaku', 'api_channel_page',
           'api_create_channel', 'api_list_channels',
           'api_post_danmaku', 'api_danmaku_to_exam']


# vim: ts=4 sw=4 sts=4 expandtab
