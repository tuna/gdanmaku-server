#!/usr/bin/env python2
# -*- coding:utf-8 -*-
import json
from flask import current_app, request, g, Response, make_response
from . import app
import xml.etree.ElementTree as ET
import re
import hashlib
import time


def jsonResponse(r):
    return Response(json.dumps(r), mimetype='application/json')


@app.route("/api/wechat", methods=["GET", "POST"])
def api_wechat_handle():
    if wechat_auth() is False:
        return "BAD TOKEN"

    if request.method == 'GET':
        echostr = request.args.get('echostr', '')
        if echostr is not '':
            return echostr

    xml_recv = ET.fromstring(request.data)
    ToUserName = xml_recv.find("ToUserName").text
    FromUserName = xml_recv.find("FromUserName").text
    Content = xml_recv.find("Content").text

    cm = g.channel_manager

    # 加入频道
    matchjoin = re.compile(ur'^加入(?:\s)*(\S+)(?:\s)*(\S+)?')
    match = matchjoin.split(Content)

    if len(match) > 2:
        if not (match[1]):
            return make_reply(
                FromUserName,
                ToUserName,
                '命令错误哦，回复"帮助"看看使用说明吧')

        channel = cm.get_channel(match[1])
        if channel is None:
            return make_reply(FromUserName, ToUserName, "木有这个频道。。。")

        if channel.is_open:
            g.r.set(''.join(['wechat.', FromUserName, '.ch_name']), match[1])
            return make_reply(FromUserName, ToUserName, "加入成功")

        # 加密频道
        if match[2] is None or (not channel.verify_pub_passwd(match[2])):
            return make_reply(FromUserName, ToUserName, "密码不对。。在试试？")

        g.r.set(''.join(['wechat.', FromUserName, '.ch_name']), match[1])
        g.r.set(''.join(['wechat.', FromUserName, '.ch_key']), match[2])
        return make_reply(FromUserName, ToUserName, "设置通道成功，发射吧")

    # 设置弹幕属性
    matchsetting = re.compile(ur"^设置(?:\s)*(\S+)(?:\s)*(\S+)?")
    match = matchsetting.split(Content)
    if len(match) > 2:
        position, color = option_trans(match[1], match[2])
        if position is None:
            return make_reply(
                FromUserName, ToUserName, "命令错误哦，回复帮助看看使用说明吧")

        g.r.set(''.join(['wechat.', FromUserName, '.ch_pos']), position)
        if color is not None:
            g.r.set(''.join(['wechat.', FromUserName, '.ch_color']), color)

        return make_reply(FromUserName, ToUserName, "设置成功，发射吧！")

    # 帮助
    matchhelp = re.compile(ur"^[帮助|help|Help]")
    match = matchhelp.match(Content)
    if match:
        return make_reply(
            FromUserName,
            ToUserName,
            ("来发射弹幕吧！\n"
             "回复 加入+频道名称+发射密码 加入频道\n"
             "如“加入 sheyifa 123456”\n"
             "加入开放频道则密码留空\n"
             "回复 设置+位置+颜色 设置弹幕属性\n"
             "如“设置 顶部 白”\n"
             "可选的位置有：飞过 顶部 底部\n"
             "可选的颜色有：蓝 白 红 黄 青 绿 紫 黑")
        )

    ch_name = g.r.get(''.join(['wechat.', FromUserName, '.ch_name']))
    ch_key = g.r.get(''.join(['wechat.', FromUserName, '.ch_key']))
    ch_pos = g.r.get(''.join(['wechat.', FromUserName, '.ch_pos']))
    ch_color = g.r.get(''.join(['wechat.', FromUserName, '.ch_color']))

    if ch_name is None:
        return make_reply(
            FromUserName, ToUserName, "还没有加入频道或者超时了 T_T")

    channel = cm.get_channel(ch_name)
    if ch_key is None:
        ch_key = ''
    if channel is None:
        return make_reply(FromUserName, ToUserName, "频道已經关闭了 T_T")

    if not channel.is_open and not channel.verify_pub_passwd(ch_key):
        return make_reply(FromUserName, ToUserName, "密码错误 T_T")

    if ch_pos is None:
        ch_pos = 'fly'
    if ch_color is None:
        ch_color = 'white'

    danmaku = {
        "text": Content,
        "style": ch_color,
        "position": ch_pos,
    }
    channel.new_danmaku(danmaku)

    return make_reply(FromUserName, ToUserName, "发射成功！")


def wechat_auth():
    token = current_app.config.get("WECHAT_TOKEN")  # your token
    query = request.args  # GET 方法附上的参数
    signature = query.get('signature', '')
    timestamp = query.get('timestamp', '')
    nonce = query.get('nonce', '')
    s = [timestamp, nonce, token]
    s.sort()
    s = ''.join(s)
    if (hashlib.sha1(s).hexdigest() == signature):
        return True
    return False


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
        u'蓝': 'blue',
        u'白': 'white',
        u'红': 'red',
        u'黄': 'yellow',
        u'青': 'cyan',
        u'绿': 'green',
        u'紫': 'purple',
        u'黑': 'black',
    }

    positions = {u'飞过': 'fly', u'顶部': 'top', u'底部': 'buttom'}

    ret = [positions.get(position, None), colors.get(color, None)]
    return ret

# vim: ts=4 sw=4 sts=4 expandtab
