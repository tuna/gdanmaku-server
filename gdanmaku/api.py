#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import json
from flask import request, g, Response
import gevent
from . import app
from .shared import RE_INVALID, DM_COLORS, DM_POSITIONS


class CoreAPIException(Exception):
    """
    Base exception class for Core API

        Callers should check self.msgs to better inform end-users.
        If self.msgs is None, it usually means the exception is
        not caused by runtime.
    """
    def __init__(self, e=None, msgs=None):
        if not isinstance(e, Exception):
            e = msgs if msgs is not None else "Unknown"
        super(CoreAPIException, self).__init__(e)
        self.msgs = msgs


class DanmakuPostException(CoreAPIException):
    """Exception class for core_api_post_danmaku"""
    def __init__(self, e=None, msgs=None):
        super(DanmakuPostException, self).__init__(e=e, msgs=msgs)


class DanmakuGetException(CoreAPIException):
    """Exception class for core_api_get_danmaku"""
    def __init__(self, e=None, msgs=None):
        super(DanmakuGetException, self).__init__(e=e, msgs=msgs)


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


def core_api_list_channels():
    channels = g.channel_manager.channels(instance=True)
    return {"channels": [c.to_dict(public=True) for c in channels]}


def core_api_channel_pub_key_verify(cname, pub_key):
    """
    A helper to verify publish password

    This is a useful workaround since we don't have any concepts related to users.

    :param cname: channel name
    :param pub_key: publish password to verify
    :return bool
    """
    return g.channel_manager.get_channel(cname).verify_pub_passwd(pub_key)


def core_api_create_channel(**kwargs):
    # not using exceptions here
    if g.channel_manager.new_channel(**kwargs) is None:
        return {"success": False, "reason": "Channel Existed"}

    return {"success": True}


def core_api_post_danmaku(cname, content,
                          exam_key=None, publish_key=None,
                          style=None, position=None):
    """
    post danmaku to server

        If the channel needs review, then danmakus posted by ordinary clients
        will be sent to examiners, and danmakus received and approved by examiners
        (In theory it is possible for examiners to change content and other things)
        will be posted as normal.

    :param cname: channel name
    :param content: text of the danmaku
    :param exam_key: None if not examiner
    :param publish_key: None if not provided
    :param style: color
    :param position
    :return True
    :exception
        DanmakuPostException: useful args:
            msgs: possible values
                channel not found
                invalid exam password
                invalid publish password
                invalid content
    """
    # does not take care of rate-limiting since
    # it is not implemented at the moment.
    cm = g.channel_manager
    channel = cm.get_channel(cname)
    if channel is None:
        # channel not found
        raise DanmakuPostException(msgs="channel not found")

    valid_exam_client = False
    if channel.need_exam:
        if exam_key is not None:
            if not channel.verify_exam_passwd(exam_key):
                # invalid exam password
                raise DanmakuPostException(msgs="invalid exam password")
            valid_exam_client = True

    if not valid_exam_client:

        if not channel.is_open:
            if publish_key is None or (not channel.verify_pub_passwd(publish_key)):
                # invalid publish password
                raise DanmakuPostException(msgs="invalid publish password")

    if (RE_INVALID.search(content) or
            (len(content.strip()) < 1) or
            (len(content.strip()) > 128)):
            # invalid content
        raise DanmakuPostException(msgs="invalid content")

    if style not in DM_COLORS:
        style = "blue"
    if position not in DM_POSITIONS:
        position = "fly"

    danmaku = {
        "text": content,
        "style": style,
        "position": position
    }
    try:
        if not channel.need_exam:
            channel.new_danmaku(danmaku)
        else:
            if valid_exam_client:
                channel.new_danmaku(danmaku)
            else:
                channel.new_danmaku_exam(danmaku)

        return True
    except Exception as e:
        raise DanmakuPostException(e=e)


def core_api_get_danmaku(cname, sub_id, sub_key=""):
    """
    subscriber gets danmakus posted by end users

    :param cname: channel name
    :param sub_id: id of subscriber
    :param sub_key: subscription password for channel
    :return channel.pop_danmakus(sname)
    :exception
        DanmakuGetException: possible msgs values:
            channel not found
            invalid subscription password
    """
    cm = g.channel_manager
    channel = cm.get_channel(cname)

    if not channel.verify_sub_passwd(sub_key):
        raise DanmakuGetException(msgs="invalid subscription password")
    try:
        return channel.pop_danmakus(sub_id)
    except Exception as e:
        if channel is None:
            raise DanmakuGetException(msgs="channel not found")
        else:
            raise DanmakuGetException(e=e)


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
           'api_post_danmaku', 'api_danmaku_to_exam',
           'CoreAPIException', 'DanmakuPostException',
           'DanmakuGetException', 'core_api_channel_pub_key_verify',
           'core_api_list_channels', 'core_api_post_danmaku',
           'core_api_get_danmaku', 'core_api_create_channel']


# vim: ts=4 sw=4 sts=4 expandtab
