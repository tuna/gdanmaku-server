#!/usr/bin/env python3
# -*- coding:utf-8 -*-

from flask import current_app, request, g, make_response
from . import app
from .api import DanmakuPostException
from .api import core_api_post_danmaku, core_api_list_channels, \
    core_api_channel_pub_key_verify
import xml.etree.ElementTree as ET
import re
import hashlib
import time


cmd_re_join = re.compile(r'^[:：]加入(?:\s+)(\S+)(?:\s*)(\S+)?')
cmd_re_opt = re.compile(r'^[:：]设置(?:\s+)(\S+)(?:\s*)(\S+)?')
cmd_re_help = re.compile(r'^[:：](帮助|help)', re.IGNORECASE)

HELP_MSG = (
    "来发射弹幕吧！\n"
    "回复 \":加入 频道名称 [发射密码]\" 加入频道\n"
    "如\":加入 sheyifa 123456\"\n"
    "加入开放频道则密码留空\n"
    "回复 \":设置 位置 [颜色]\" 设置弹幕属性\n"
    "如 \":设置 顶部 白\" \n"
    "可选的位置有：飞过 顶部 底部\n"
    "可选的颜色有：蓝 白 红 黄 青 绿 紫 黑")


def redis_key(key):
    return current_app.config.get("REDIS_PREFIX") + "wechat." + key


@app.route("/api/wechat", methods=["GET", "POST"])
def api_wechat_handle():
    # verify whether it is sent by wechat
    if not wechat_verify():
        return "BAD TOKEN", 400

    # respond to echo
    if request.method == 'GET':
        echostr = request.args.get('echostr', '')
        return echostr

    # obtain info from request data
    xml_recv = ET.fromstring(request.data)
    ToUserName = xml_recv.find("ToUserName").text
    FromUserName = xml_recv.find("FromUserName").text

    # handle special event related to wechat
    if xml_recv.find("MsgType").text == "event":
        event = xml_recv.find("Event").text
        event_key = xml_recv.find("EventKey")
        event_key = event_key.text if event_key is not None else ""
        return handle_event(FromUserName, ToUserName, event, event_key)

    Content = xml_recv.find("Content").text

    # handle command sent by end-user
    if Content[0] in (':', '：'):
        return handle_command(FromUserName, ToUserName, Content)

    # handle danmaku posting
    # FIXME: nasty handling of bytes and str,
    # consider adding decode_responses=True in redis.StrictRedis()
    ch_name = g.r.get(redis_key(FromUserName + ".ch_name"))
    if ch_name is None:
        return make_reply(FromUserName, ToUserName,
                          "还没有加入频道或者超时，回复\":帮助\"获取帮助。")
    else: ch_name = ch_name.decode()
    ch_key = g.r.get(redis_key(FromUserName + ".ch_key"))
    if ch_key is not None: ch_key = ch_key.decode()
    ch_pos = g.r.get(redis_key(FromUserName + ".ch_pos"))
    if ch_pos is not None: ch_pos = ch_pos.decode()
    ch_color = g.r.get(redis_key(FromUserName + ".ch_color"))
    if ch_color is not None: ch_color = ch_color.decode()

    kwargs = {
        "cname": ch_name,
        "content": Content,
        "exam_key": None,
        "publish_key": ch_key,
        "style": ch_color,
        "position": ch_pos
    }

    try:
        core_api_post_danmaku(**kwargs)
        return "success"
    except DanmakuPostException as e:
        EXCEPTION_INFO = {
            "channel not found":
                "还没有加入频道或者已经关闭，回复\":帮助\"获取帮助。",
            "invalid publish password": "密码错误 T_T",
            "invalid content": "弹幕包含怪异字符或过长 T_T"
        }
        try:
            return make_reply(FromUserName, ToUserName, EXCEPTION_INFO[e.msgs])
        except KeyError:
            if e.msgs is not None:
                return make_reply(FromUserName, ToUserName,
                                  "神秘问题呢，再试试？")
            else:
                return make_reply(FromUserName, ToUserName,
                                  "弹幕程序遇到神秘问题呢，问问弹幕墙的人吧。")


def handle_event(FromUserName, ToUserName, Event, EventKey=""):
    if Event.lower() == "subscribe" and not EventKey:
        return make_reply(FromUserName, ToUserName, HELP_MSG)
    elif Event.lower() == "unsubscribe":
        g.r.delete(
            redis_key(FromUserName + '.ch_pos'),
            redis_key(FromUserName + '.ch_color')
        )

    return "success"


def handle_command(FromUserName, ToUserName, Content):

    # 加入频道
    match = cmd_re_join.match(Content)
    if match:
        mchan, mpass = match.groups()
        if not mchan:
            return make_reply(
                FromUserName,
                ToUserName,
                '命令错误哦，回复":帮助"看看使用说明吧')

        for ch in core_api_list_channels()["channels"]:
            if ch['name'] == mchan:
                if ch['is_open']:
                    ckey = redis_key(FromUserName + '.ch_name')
                    g.r.set(ckey, mchan)
                    if ch['ttl'] > 0:
                        g.r.expire(ckey, ch['ttl'])
                    return make_reply(FromUserName, ToUserName, "加入成功")
                if mpass is None or (not core_api_channel_pub_key_verify(mchan, mpass)):
                    return make_reply(FromUserName, ToUserName, "密码不对。。再试试？")
                ckey = redis_key(FromUserName + '.ch_name')
                pkey = redis_key(FromUserName + '.ch_key')
                g.r.set(ckey, mchan)
                g.r.set(pkey, mpass)
                if ch['ttl'] > 0:
                    g.r.expire(ckey, ch['ttl'])
                    g.r.expire(pkey, ch['ttl'])
                return make_reply(FromUserName, ToUserName, "设置通道成功，发射吧")
        return make_reply(FromUserName, ToUserName, "木有这个频道。。。")

    # 设置弹幕属性
    match = cmd_re_opt.match(Content)
    if match:
        position, color = option_trans(*match.groups())
        if position is None:
            return make_reply(
                FromUserName,
                ToUserName,
                "命令错误哦，回复\":帮助\"看看使用说明吧")

        g.r.set(redis_key(FromUserName + '.ch_pos'), position)
        if color is not None:
            g.r.set(redis_key(FromUserName + '.ch_color'), color)

        return make_reply(FromUserName, ToUserName, "设置成功，发射吧！")

    # 帮助
    match = cmd_re_help.match(Content)
    if match:
        return make_reply(
            FromUserName,
            ToUserName,
            HELP_MSG,
        )

    return make_reply(
        FromUserName, ToUserName, "命令错误哦，回复\":帮助\"看看使用说明吧")


def wechat_verify():
    token = current_app.config.get("WECHAT_TOKEN")  # your token
    query = request.args  # GET 方法附上的参数
    signature = query.get('signature', '')
    timestamp = query.get('timestamp', '')
    nonce = query.get('nonce', '')
    s = ''.join(sorted([timestamp, nonce, token]))
    return hashlib.sha1(s.encode()).hexdigest() == signature


def make_reply(touser, fromuser, content):
    tmpl = ("<xml>"
            "<ToUserName><![CDATA[{touser}]]></ToUserName>"
            "<FromUserName><![CDATA[{fromuser}]]></FromUserName>"
            "<CreateTime>{ts}</CreateTime>"
            "<MsgType><![CDATA[text]]></MsgType>"
            "<Content><![CDATA[{content}]]></Content>"
            "<FuncFlag>0</FuncFlag>"
            "</xml>")

    response = make_response(
        tmpl.format(
            touser=touser,
            fromuser=fromuser,
            ts=int(time.time()),
            content=content,
        )
    )

    response.content_type = 'application/xml'
    return response


def option_trans(position, color):
    colors = {
        '蓝': 'blue',
        '白': 'white',
        '红': 'red',
        '黄': 'yellow',
        '青': 'cyan',
        '绿': 'green',
        '紫': 'purple',
        '黑': 'black',
        '蓝色': 'blue',
        '白色': 'white',
        '红色': 'red',
        '黄色': 'yellow',
        '青色': 'cyan',
        '绿色': 'green',
        '紫色': 'purple',
        '黑色': 'black',
    }

    positions = {
        '飞过': 'fly',
        '顶部': 'top',
        '底部': 'bottom',
        '飞': 'fly',
        '顶': 'top',
        '底': 'bottom',
    }

    ret = [positions.get(position, None), colors.get(color, None)]
    return ret


__all__ = ['api_wechat_handle', ]

# vim: ts=4 sw=4 sts=4 expandtab
