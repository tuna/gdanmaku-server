#!/usr/bin/env python3
# -*- coding:utf-8 -*-

from flask import current_app, request, g, Response
from . import app
from .api import DanmakuPostException
from .api import core_api_post_danmaku, core_api_list_channels, \
    core_api_channel_pub_key_verify
import re
import json
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
    return current_app.config.get("REDIS_PREFIX") + "telegram." + key


@app.route("/api/telegram/<tg_token>", methods=["POST"])
def api_telegram_handle(tg_token):
    # valid requests from telegram
    if tg_token != current_app.config.get("TELEGRAM_TOKEN"):
        return "Bad Request", 400
    # a valid Update object
    if "update_id" not in request.json.keys():
        return "Bad Request", 400
    # only handle ordinary Message objects ATM
    if "message" not in request.json.keys():
        print(request.json)
        return "OK", 200
    message = request.json["message"]
    # ignore messages that are too old
    if (time.time() - message["date"]) > 60:
        return "OK", 200
    # ignore forwarded messages
    if "forward_date" in message.keys():
        return "OK", 200
    # ignore channel messages
    if "from" not in message.keys():
        return "OK", 200
    # extract actual message string
    text = message["text"]
    chat = message["chat"]
    user_from = message["from"]
    user_id = str(user_from["id"])
    # handle command sent by end-user
    if text[0] in (':', '：'):
        return handle_command(chat["id"], user_id, text)
    # handle danmaku posting
    cname = g.r.get(redis_key(user_id + ".ch_name"))
    if cname is None:
        return message_make(chat["id"],
                            "还没有加入频道，回复\":帮助\"获取帮助。")

    kwargs = {
        "cname": cname,
        "content": text,
        "exam_key": None,
        "publish_key": g.r.get(redis_key(user_id + ".ch_key")),
        "style": g.r.get(redis_key(user_id + ".ch_color")),
        "position": g.r.get(redis_key(user_id + ".ch_pos"))
    }
    try:
        core_api_post_danmaku(**kwargs)
        return "OK", 200
    except DanmakuPostException as e:
        EXCEPTION_INFO = {
            "channel not found":
                "还没有加入频道或者已经超时，回复\":帮助\"获取帮助。",
            "invalid publish password": "密码错误 T_T",
            "invalid content": "弹幕包含怪异字符或过长 T_T"
        }
        try:
            return message_make(chat["id"],
                                EXCEPTION_INFO[e.msgs])
        except KeyError:
            if e.msgs is not None:
                return message_make(chat["id"],
                                    "神秘问题呢，回复\":帮助\"试试？")
            else:
                return message_make(chat["id"],
                                    "弹幕程序遇到神秘问题呢，问问弹幕墙的人吧。")


def handle_command(chat_id, user_id, Content):
    # 加入频道
    match = cmd_re_join.match(Content)
    if match:
        mchan, mpass = match.groups()
        if not mchan:
            return message_make(chat_id,
                                '命令错误哦，回复":帮助"看看使用说明吧')

        for ch in core_api_list_channels()["channels"]:
            # channel exists
            if ch['name'] == mchan:
                # open channel
                if ch['is_open']:
                    ckey = redis_key(user_id + '.ch_name')
                    g.r.set(ckey, mchan)
                    if ch['ttl'] > 0:
                        g.r.expire(ckey, ch['ttl'])
                    return message_make(chat_id, "加入成功")
                # channel with publish password
                if mpass is None or (not core_api_channel_pub_key_verify(mchan, mpass)):
                    return message_make(chat_id, "密码不对。。再试试？")
                ckey = redis_key(user_id + '.ch_name')
                pkey = redis_key(user_id + '.ch_key')
                g.r.set(ckey, mchan)
                g.r.set(pkey, mpass)
                if ch['ttl'] > 0:
                    g.r.expire(ckey, ch['ttl'])
                    g.r.expire(pkey, ch['ttl'])
                return message_make(chat_id, "设置通道成功，发射吧")
        return message_make(chat_id, "木有这个频道。。。")

    # 设置弹幕属性
    match = cmd_re_opt.match(Content)
    if match:
        position, color = option_trans(*match.groups())
        if position is None:
            return message_make(
                chat_id,

                "命令错误哦，回复\":帮助\"看看使用说明吧")

        g.r.set(redis_key(user_id + '.ch_pos'), position)
        if color is not None:
            g.r.set(redis_key(user_id + '.ch_color'), color)

        return message_make(chat_id, "设置成功，发射吧！")

    # 帮助
    match = cmd_re_help.match(Content)
    if match:
        return message_make(
            chat_id,

            HELP_MSG,
        )

    return message_make(
        chat_id, "命令错误哦，回复\":帮助\"看看使用说明吧")


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


def message_make(chat_id, text):
    return method_call_make("sendMessage", {"chat_id": chat_id, "text": text})


def method_call_make(method, params):
    payload = {"method": method, }
    for key, value in params.items():
        payload[key] = value
    return Response(json.dumps(payload), mimetype='application/json')


__all__ = ['api_telegram_handle', ]
