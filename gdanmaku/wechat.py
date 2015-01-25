#!/usr/bin/env python2
# -*- coding:utf-8 -*-
from flask import current_app, request, g, Response, make_response
from . import app
import xml.etree.ElementTree as ET
import re
import hashlib
import time


cmd_re_join = re.compile(ur'^[:：]加入(?:\s+)(\S+)(?:\s*)(\S+)?')
cmd_re_opt = re.compile(ur'^[:：]设置(?:\s+)(\S+)(?:\s*)(\S+)?')
cmd_re_help = re.compile(ur'^[:：](帮助|help)', re.IGNORECASE)


def redis_key(key):
    return current_app.config.get("REDIS_PREFIX") + "wechat." + key


@app.route("/api/wechat", methods=["GET", "POST"])
def api_wechat_handle():
    if not wechat_verify():
        return "BAD TOKEN", 400

    if request.method == 'GET':
        echostr = request.args.get('echostr', '')
        return echostr

    xml_recv = ET.fromstring(request.data)
    ToUserName = xml_recv.find("ToUserName").text
    FromUserName = xml_recv.find("FromUserName").text
    Content = xml_recv.find("Content").text

    if Content[0] in (u':', u'：'):
        return handle_command(FromUserName, ToUserName, Content)

    cm = g.channel_manager

    ch_name = g.r.get(redis_key(FromUserName + ".ch_name"))
    ch_key = g.r.get(redis_key(FromUserName + ".ch_key")) or ''
    ch_pos = g.r.get(redis_key(FromUserName + ".ch_pos"))
    ch_color = g.r.get(redis_key(FromUserName + ".ch_color"))

    if ch_name is None:
        return make_reply(
            FromUserName,
            ToUserName,
            u"还没有加入频道或者超时，回复\":帮助\"获取帮助。"
        )

    channel = cm.get_channel(ch_name)
    if channel is None:
        return make_reply(FromUserName, ToUserName, u"频道已經关闭了 T_T")

    if not channel.is_open and not channel.verify_pub_passwd(ch_key):
        return make_reply(FromUserName, ToUserName, u"密码错误 T_T")

    danmaku = {
        "text": Content,
        "style": ch_color or 'blue',
        "position": ch_pos or 'fly',
    }
    channel.new_danmaku(danmaku)

    return make_reply(FromUserName, ToUserName, u"发射成功！")


def handle_command(FromUserName, ToUserName, Content):
    cm = g.channel_manager

    # 加入频道
    match = cmd_re_join.match(Content)
    if match:
        mchan, mpass = match.groups()
        if not mchan:
            return make_reply(
                FromUserName,
                ToUserName,
                u'命令错误哦，回复"帮助"看看使用说明吧')

        channel = cm.get_channel(mchan)
        ttl = g.r.ttl(channel.key)
        if channel is None:
            return make_reply(FromUserName, ToUserName, u"木有这个频道。。。")

        if channel.is_open:
            ckey = redis_key(FromUserName + '.ch_name')
            g.r.set(ckey, mchan)
            if ttl > 0:
                g.r.expire(ckey, ttl)
            return make_reply(FromUserName, ToUserName, u"加入成功")

        # 加密频道
        if mpass is None or (not channel.verify_pub_passwd(mpass)):
            return make_reply(FromUserName, ToUserName, u"密码不对。。在试试？")

        ckey = redis_key(FromUserName + '.ch_name')
        pkey = redis_key(FromUserName + '.ch_key')
        g.r.set(ckey, mchan)
        g.r.set(pkey, mpass)
        if ttl > 0:
            g.r.expire(ckey, ttl)
            g.r.expire(pkey, ttl)

        return make_reply(FromUserName, ToUserName, u"设置通道成功，发射吧")

    # 设置弹幕属性
    match = cmd_re_opt.match(Content)
    if match:
        position, color = option_trans(*match.groups())
        if position is None:
            return make_reply(
                FromUserName,
                ToUserName,
                u"命令错误哦，回复\":帮助\"看看使用说明吧")

        g.r.set(redis_key(FromUserName + '.ch_pos'), position)
        if color is not None:
            g.r.set(redis_key(FromUserName + '.ch_color'), color)

        return make_reply(FromUserName, ToUserName, u"设置成功，发射吧！")

    # 帮助
    match = cmd_re_help.match(Content)
    if match:
        return make_reply(
            FromUserName,
            ToUserName,
            (u"来发射弹幕吧！\n"
             u"回复 \":加入 频道名称 [发射密码]\" 加入频道\n"
             u"如\":加入 sheyifa 123456\"\n"
             u"加入开放频道则密码留空\n"
             u"回复 \":设置 位置 [颜色]\" 设置弹幕属性\n"
             u"如 \":设置 顶部 白\" \n"
             u"可选的位置有：飞过 顶部 底部\n"
             u"可选的颜色有：蓝 白 红 黄 青 绿 紫 黑")
        )

    return make_reply(
        FromUserName, ToUserName, u"命令错误哦，回复\":帮助\"看看使用说明吧")


def wechat_verify():
    token = current_app.config.get("WECHAT_TOKEN")  # your token
    query = request.args  # GET 方法附上的参数
    signature = query.get('signature', '')
    timestamp = query.get('timestamp', '')
    nonce = query.get('nonce', '')
    s = ''.join(sorted([timestamp, nonce, token]))
    return hashlib.sha1(s).hexdigest() == signature


def make_reply(touser, fromuser, content):
    tmpl = (u"<xml>"
            u"<ToUserName><![CDATA[{touser}]]></ToUserName>"
            u"<FromUserName><![CDATA[{fromuser}]]></FromUserName>"
            u"<CreateTime>{ts}</CreateTime>"
            u"<MsgType><![CDATA[text]]></MsgType>"
            u"<Content><![CDATA[{content}]]></Content>"
            u"<FuncFlag>0</FuncFlag>"
            u"</xml>")

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
        u'蓝色': 'blue',
        u'白色': 'white',
        u'红色': 'red',
        u'黄色': 'yellow',
        u'青色': 'cyan',
        u'绿色': 'green',
        u'紫色': 'purple',
        u'黑色': 'black',
    }

    positions = {
        u'飞过': 'fly',
        u'顶部': 'top',
        u'底部': 'bottom',
        u'飞': 'fly',
        u'顶': 'top',
        u'底': 'bottom',
    }

    ret = [positions.get(position, None), colors.get(color, None)]
    return ret


__all__ = ['api_wechat_handle', ]

# vim: ts=4 sw=4 sts=4 expandtab
