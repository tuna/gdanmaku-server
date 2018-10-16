#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import json
from flask import request, g, Response
from . import app
from .api import DanmakuPostException, DanmakuGetException, core_api_list_channels, \
    core_api_create_channel, core_api_post_danmaku, core_api_get_danmaku


def jsonResponse(r):
    res = Response(json.dumps(r), mimetype='application/json')
    res.headers.add('Access-Control-Allow-Origin', '*')
    res.headers.add(
        'Access-Control-Allow-Headers',
        'Content-Type,X-GDANMAKU-AUTH-KEY,'
        # 'X-GDANMAKU-SUBSCRIBER-ID,X-GDANMAKU-TOKEN'
        'X-GDANMAKU-SUBSCRIBER-ID'
    )
    res.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    return res


@app.route("/api/v1/channels", methods=["GET"])
def api_list_channels():
    return jsonResponse(core_api_list_channels())


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

    core_api_response = core_api_create_channel(**kwargs)
    if not core_api_response["success"]:
        return core_api_response["reason"], 409

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
    form = request.json if request.json else request.form
    # _token = request.headers.get("X-GDANMAKU-TOKEN")
    # if _token is None:
    #     return "Token is required", 400
    # try:
    #     ttype, token = _token.split(':')
    # except ValueError:
    #     return "Bad Request", 400
    # # TODO: Implement rate-limiting
    # if ttype == "WEB":
    #     pass
    # elif ttype == "APP":
    #     pass
    # else:
    #     return "Bad Request", 400

    try:
        kwargs = {
            "cname": cname,
            "exam_key": request.headers.get("X-GDANMAKU-EXAM-KEY"),
            "publish_key": request.headers.get("X-GDANMAKU-AUTH-KEY"),
            "content": form['content'],
            "style": form.get("color"),
            "position": form.get("position")
        }
    except:
        return "Bad Request", 400
    try:
        core_api_post_danmaku(**kwargs)
        # return jsonResponse({"token": token, "ret": "OK"})
        return jsonResponse({"ret": "OK"})
    except DanmakuPostException as e:
        EXCEPTION_INFO = {
            "channel not found": ("Not Found", 404),
            "invalid exam password": ("Bad Exam Password", 403),
            "invalid publish password": ("Forbidden", 403),
            "invalid content": ("Bad Request", 400)
        }
        try:
            return EXCEPTION_INFO[e.msgs]
        except KeyError:
            if e.msgs is not None:
                return "Bad Request", 400
            else:
                return "Internal Error", 500


@app.route("/api/v1/channels/<cname>/danmaku", methods=["GET"])
@app.route("/api/v1.1/channels/<cname>/danmaku", methods=["GET"])
def api_channel_danmaku(cname):
    try:
        kwargs = {
            "cname": cname,
            "sub_id": request.headers.get("X-GDANMAKU-SUBSCRIBER-ID", "ALL"),
            "sub_key": request.headers.get("X-GDANMAKU-AUTH-KEY", "")
        }
    except:
        return "Bad Request", 400
    try:
        return jsonResponse(core_api_get_danmaku(**kwargs))
    except DanmakuGetException as e:
        EXCEPTION_INFO = {
            "channel not found": ("Not Found", 404),
            "invalid subscription password": ("Forbidden", 403)
        }
        try:
            return EXCEPTION_INFO[e.msgs]
        except KeyError:
            if e.msgs is not None:
                return "Bad Request", 400
            else:
                return "Internal Error", 500


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
