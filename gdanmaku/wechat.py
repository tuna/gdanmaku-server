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

@app.route("/api/wechat", methods=["GET","POST"])
def api_wechat_handle():
    if wechat_auth() is False :
        return "BAD TOKEN"
    if request.method is 'GET' :
    	echostr = request.args.get('echostr', '')
        if echostr is not '':
            return echostr    
    xml_recv = ET.fromstring(request.data)  
    ToUserName = xml_recv.find("ToUserName").text  
    FromUserName = xml_recv.find("FromUserName").text  
    Content = xml_recv.find("Content").text
    matchjoin = re.compile('^join(?:\s)(\S+)(?:\s)(\S+)')
    match = matchjoin.split(Content)
    cm = g.channel_manager
    print match
    if len( match ) is 4:
        if not (match[1] and match[2]):
            return make_return(FromUserName,ToUserName,"命令错误哦，回复帮助看看使用说明吧")
        channel = cm.get_channel(match[1])
        if channel is None:
            return make_return(FromUserName, ToUserName,"木有这个通道。。。")
        key = match[2]
        if key is None or (not channel.verify_pub_passwd(key)):
            return make_return(FromUserName, ToUserName,"密码不对。。在试试？")
        g.r.set(''.join(['wechat.', FromUserName, '.ch_name']), match[1])
        g.r.set(''.join(['wechat.', FromUserName, '.ch_key']), match[2]);
        return make_return(FromUserName, ToUserName, "设置通道成功，发射吧")
    matchsetting = re.compile("^set(?:\s)(\S+)(?:\s)(\S+)")
    match = matchsetting.split(Content)
    if len(match) > 2:
        option = option_trans(match[1],match[2])
        if option[0] is None:
            return make_return(FromUserName, ToUserName, "命令错误哦，回复帮助看看使用说明吧")
        g.r.set(''.join(['wechat.', FromUserName,'.ch_pos']),option[0])
        if option[1] is not None :
            g.r.set(''.join(['wechat.', FromUserName,'.ch_color']),option[1])
        return make_return(FromUserName, ToUserName, "设置成功，发射吧！")
    matchhelp = re.compile("^[help|Help]")
    match = matchhelp.match(Content)
    if match:
        return make_return(FromUserName, ToUserName, "来发射弹幕吧！\n回复 加入+频道名称+发射密码 加入频道\n如“加入 sheyifa 123456”\n回复 设置+位置+颜色 设置弹幕属性\n如“设置 顶部 白”\n可选的位置有：飞过 顶部 底部\n可选的颜色有：蓝 白 红 黄 青 绿 紫 黑")
    ch_name = g.r.get(''.join(['wechat.',FromUserName,'.ch_name']))
    ch_key = g.r.get(''.join(['wechat.', FromUserName, '.ch_key']))
    ch_pos = g.r.get(''.join(['wechat.',FromUserName, '.ch_pos']))
    ch_color = g.r.get(''.join(['wechat.', FromUserName, '.ch_color']))
    if ch_name is None:
        return make_return(FromUserName, ToUserName, "还没有加入通道或者超时了T_T")
    channel = cm.get_channel(ch_name)
    if channel is None:
        return make_return(FromUserName, ToUserName, "频道已經关闭了T_T")
    if not channel.verify_pub_passwd(ch_key):
        return make_return(FromUserName, ToUserName, "密码错误T_T")
    if ch_pos is None:
        ch_pos = 'fly'
    if ch_color is None:
        ch_color = 'white'
    danmaku = {
        "text": Content,
        "style": ch_color,
        "position": ch_pos
    }
    channel.new_danmaku(danmaku)
    return make_return(FromUserName, ToUserName, "发射成功！")


def wechat_auth():    
    token = current_app.config.get("WECHAT_TOKEN") # your token  
    query = request.args  # GET 方法附上的参数  
    signature = query.get('signature', '')  
    timestamp = query.get('timestamp', '')  
    nonce = query.get('nonce', '')  
    s = [timestamp, nonce, token]  
    s.sort()  
    s = ''.join(s)  
    if ( hashlib.sha1(s).hexdigest() == signature ):    
        return True
    return True #False
  
def make_return(fromuser, touser,content):
    reply = "<xml><ToUserName><![CDATA[%s]]></ToUserName><FromUserName><![CDATA[%s]]></FromUserName><CreateTime>%s</CreateTime><MsgType><![CDATA[text]]></MsgType><Content><![CDATA[%s]]></Content><FuncFlag>0</FuncFlag></xml>"
    response = make_response( reply % (touser, fromuser, str(int(time.time())), content ) )
    response.content_type = 'application/xml'
    return response

def option_trans(position, color):
    colors = {'蓝':'blue','白':'white','红':'red','黄':'yellow','青':'cyan','绿':'green','紫':'purple','黑':'black'}
    positions = {'飞过': 'fly','顶部': 'top','底部': 'buttom'}
    if postions[position] is not None:
        ret[0] = positions[position]
    else :
        ret[0] = None
    if colors[color] is not None:
        ret[1] = colors[position]
    else :
        ret[1] = None
    return ret

#@app.route("/api/v1/channels", methods=["GET"])
#def api_list_channels():
#    channels = g.channel_manager.channels(instance=True)
#    return jsonResponse({'channels': [c.to_dict(public=True) for c in channels]})
#
#
#@app.route("/api/v1/channels", methods=["POST"])
#def api_create_channel():
#    form = request.json if request.json else request.form
#
#    try:
#        kwargs = {
#            "name": form["name"],
#            "desc": form["desc"],
#            "ttl": int(form.get("ttl", 2)),
#            "sub_passwd": form["sub_passwd"],
#            "pub_passwd": form.get("pub_passwd", ""),
#        }
#    except:
#        return "Invalid Request", 400
#
#    if g.channel_manager.new_channel(**kwargs) is None:
#        return "Channel Existed", 409
#
#    return jsonResponse({"url": "/channel/{}".format(form["name"])})
#
#
#@app.route("/api/v1/channels/<cname>", methods=["GET"])
#def api_channel_page(cname):
#    pass
#
#
#@app.route("/api/v1/channels/<cname>/danmaku", methods=["POST"])
#def api_post_danmaku(cname):
#    cm = g.channel_manager
#
#    channel = cm.get_channel(cname)
#    if channel is None:
#        return "Not Found", 404
#
#    if not channel.is_open:
#        key = request.headers.get("X-GDANMAKU-AUTH-KEY")
#        if key is None or (not channel.verify_pub_passwd(key)):
#            return "Forbidden", 403
#
#    if request.json:
#        danmaku = {
#            "text": request.json["content"],
#            "style": request.json.get("color", "white"),
#            "position": request.json.get("position", "fly")
#        }
#    else:
#        danmaku = {
#            "text": request.form["content"],
#            "style": request.form.get("style", "white"),
#            "position": request.form.get("position", "fly")
#        }
#
#    # interface.new_danmaku(content)
#    channel.new_danmaku(danmaku)
#    return "OK"
#
#
#@app.route("/api/v1/channels/<cname>/danmaku", methods=["GET"])
#def api_channel_danmaku(cname):
#    cm = g.channel_manager
#
#    channel = cm.get_channel(cname)
#    if channel is None:
#        return "Not Found", 404
#
#    key = request.headers.get("X-GDANMAKU-AUTH-KEY")
#    if key is None or (not channel.verify_sub_passwd(key)):
#        return "Forbidden", 403
#
#    r = channel.pop_danmakus("ALL")
#    return jsonResponse(r)
#
#
#@app.route("/api/v1.1/channels/<cname>/danmaku", methods=["GET"])
#def api_channel_danmaku_1(cname):
#    cm = g.channel_manager
#
#    channel = cm.get_channel(cname)
#    if channel is None:
#        return "Not Found", 404
#
#    sname = request.headers.get("X-GDANMAKU-SUBSCRIBER-ID", "ALL")
#    key = request.headers.get("X-GDANMAKU-AUTH-KEY")
#    if key is None or (not channel.verify_sub_passwd(key)):
#        return "Forbidden", 403
#
#    r = channel.pop_danmakus(sname)
#    return jsonResponse(r)


# vim: ts=4 sw=4 sts=4 expandtab
