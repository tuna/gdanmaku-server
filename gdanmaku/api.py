#!/usr/bin/env python3
# -*- coding:utf-8 -*-
from flask import g
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


__ALL__ = ['CoreAPIException', 'DanmakuPostException',
           'DanmakuGetException', 'core_api_list_channels',
           'core_api_channel_pub_key_verify', 'core_api_create_channel',
           'core_api_post_danmaku', 'core_api_get_danmaku', ]
