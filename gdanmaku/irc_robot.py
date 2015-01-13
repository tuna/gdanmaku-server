#!/usr/bin/env python2
# -*- coding:utf-8 -*-
import re
from random import randint
from gevent import socket, spawn, sleep

from .shared import DM_COLORS, DM_COLOR_TRANS, DM_POSITIONS, DM_POSITION_TRANS


class IRCManager(object):

    def __init__(self, app, chan_mgr):
        self.app = app
        self.cm = chan_mgr
        self.bot_list = {}
        IRCbot.REDIS_PREFIX = app.config.get("REDIS_PREFIX")

    def connect_channel(self, dm_chan, irc_chan):
        self.bot_list[dm_chan] = IRCbot(
            manager=self,
            host="card.freenode.net",
            port=6666,
            nick="dmbot",
            dm_chan=self.cm.get_channel(dm_chan),
            irc_chan=irc_chan,
            timeout=10,
        )

        spawn(self.bot_list[dm_chan].run)


class IRCbot(object):
    REALNAME = "TUNA DanmakuBot"
    REDIS_PREFIX = ""

    def __init__(self, manager, host, port, nick, dm_chan,
                 irc_chan=None, timeout=60):

        self.HOST = host
        self.PORT = port
        self.NICK = nick
        self._nick = nick
        self.channel = irc_chan
        self.dm_chan = dm_chan
        self._timeout = timeout

        self.method = "MSG"  # CHANNEL OR MSG
        self.manager = manager
        self.r = self.manager.cm.r

    def run(self):

        if not self.manager:
            return None

        self.irc_init()

        rspace = re.compile(r'\s+')
        for line in self.get_server_msg():
            # print(line)
            if not line:
                print("bot stopped")
                break

            if line[0] == ':':
                prefix, line = rspace.split(line, 1)
                nick = prefix.split('!')[0][1:]
            else:
                nick = None

            cmd, params = rspace.split(line, 1)

            if cmd == 'PING':
                self.do_pong(params)

            elif cmd == 'PONG':
                # print("PONG")
                pass

            elif cmd == 'JOIN':
                print("joined channel %s" % params)
                if not params == self.channel:
                    self.online = False

            elif cmd == 'PRIVMSG':
                targets, content = rspace.split(params, 1)
                if not content[0] == ':':
                    continue

                content = content[1:]
                self.handle_text_message(nick, targets, content)

            elif cmd == '433':
                # nick name existed
                self.NICK = self.gen_nickname(self._nick)
                self.do_login(self.NICK)

            elif cmd == '001':
                # welcome message
                # self.checked = True
                self.irc_online = True
                self.do_join()

            else:
                # Other commands
                continue

    def handle_text_message(self, nick, targets, content):
        if nick == self.NICK:
            return

        for target in targets.split(','):
            if target[0] == '#' and self.method != 'CHANNEL':
                self.do_privmsg(targets, "Please msg me in private")
                continue

            if content.startswith(".dmopt"):
                tokens = content.split()
                if len(tokens) == 1:
                    self.do_privmsg(targets, "invalid command!")
                    continue
                tokens.pop(0)
                color = tokens.pop(0)
                if color not in DM_COLORS:
                    if color not in DM_COLOR_TRANS:
                        self.do_privmsg(targets, 'invalid color!')
                        continue
                    color = DM_COLOR_TRANS[color]

                if len(tokens) == 0:
                    self.set_danmaku_pref(color)
                else:
                    pos = tokens.pop(0)
                    if pos not in DM_POSITIONS:
                        if pos not in DM_POSITION_TRANS:
                            self.do_privmsg(targets, 'invalid position!')
                            continue
                        pos = DM_POSITION_TRANS[pos]
                    self.set_danmaku_pref(nick, color, pos)

            elif content.startswith(".dmhelp"):
                if self.method == "CHANNEL":
                    self.do_privmsg(targets, "type anything to send danmaku")
                else:
                    self.do_privmsg(targets, "'/msg %s ooxx' to send danmaku" % self.NICK)

                self.do_privmsg(targets, ".dmopt <color> [position]: set danmaku options")
                self.do_privmsg(targets, ".dmhelp: print this message")

            else:
                color, pos = self.get_danmaku_pref(nick)
                if self.shoot(content, color, pos):
                    self.do_privmsg(nick, 'Shoot!')
                else:
                    self.do_privmsg(targets, 'Server Error!')

    def set_danmaku_pref(self, nick, color, pos='fly'):
        ckey = self.REDIS_PREFIX + \
            ".".join(["IRC", self.channel, nick, "color"])
        pkey = self.REDIS_PREFIX + \
            ".".join(["IRC", self.channel, nick, "pos"])
        self.r.set(ckey, color)
        if self.dm_chan._ttl > 0:
            self.r.expire(ckey, self.dm_chan._ttl * 60 * 60)
        self.r.set(pkey, pos)
        if self.dm_chan._ttl > 0:
            self.r.expire(pkey, self.dm_chan._ttl * 60 * 60)
        self.do_privmsg(nick, "danmaku options set as: %s, %s" % (color, pos))

    def get_danmaku_pref(self, nick):
        ckey = self.REDIS_PREFIX + \
            ".".join(["IRC", self.channel, nick, "color"])
        pkey = self.REDIS_PREFIX + \
            ".".join(["IRC", self.channel, nick, "pos"])
        return (self.r.get(ckey) or "blue", self.r.get(pkey) or "fly")

    def get_server_msg(self):
        # Generator of server messages
        last_buf = ''
        retry = 3
        while 1:
            try:
                buf = self._ss.recv(1024)
            except socket.timeout:
                retry -= 1
                if retry >= 0:
                    self.do_ping()
                else:
                    print("Reconnect")
                    self._ss.close()
                    self.irc_init()
                continue
            except socket.error:
                yield None

            if not buf:
                yield None

            retry = 3
            lines = (last_buf + buf).split('\r\n')
            last_buf = '' if buf.endswith('\r\n') else lines.pop()
            for line in lines:
                if line:
                    yield line

    def shoot(self, content, color='white', position='fly'):
        # if not self.dmch.is_open:
        #     key = self.dmpw
        #     if key is None or (not self.dmch.verify_pub_passwd(key)):
        #         return False

        danmaku = {
            "text": content,
            "style": color,
            "position": position
        }
        self.dm_chan.new_danmaku(danmaku)
        return True

    def irc_init(self):
        self.irc_online = False
        self.do_connect()
        self.do_login()

    def do_connect(self):
        self._ss = socket.socket()
        self._ss.settimeout(self._timeout)
        self._ss.connect((self.HOST, self.PORT), )

    def do_login(self, nick=None):
        if nick is None:
            nick = self.NICK
        self._ss.send("NICK %s\r\n" % nick)
        self._ss.send(
            "USER %s %s * :%s\r\n" % (nick, self.HOST, self.REALNAME))

    def do_join(self):
        if self.channel is None:
            self.method = "MSG"
        else:
            self._ss.send("JOIN %s\r\n" % self.channel)
            self.method = "CHANNEL"
            self.do_privmsg(
                self.channel,
                ("主人, 我是你的弹幕喵！"
                 "发送 .dmhelp 查询我的正确打开方式喵！")
            )

    def do_ping(self):
        # print("PING")
        self._ss.send("PING :TIMEOUTCHECK\r\n")

    def do_pong(self, params):
        self._ss.send("PONG " + params + '\r\n')

    def do_privmsg(self, target, msg):
        # print(' '.join(["PRIVMSG", target, ':'+msg+'\r\n']))
        self._ss.send(' '.join(["PRIVMSG", target, ':'+msg+'\r\n']))

    def stop(self):
        self._ss.send("QUIT bye~\r\n")
        self._ss.close()

    @classmethod
    def gen_nickname(cls, nickname):
        return "%s%d" % (nickname, randint(1000, 9999))


def test():
    thread1 = IRCbot()
    thread1.HOST = "card.freenode.net"
    thread1.PORT = 6666
    thread1.channel = "#tuna"
    thread1.method = "CHANNEL"
    thread1.check()
    thread1.start()
    while(1):
        sleep(1000)
    return

if __name__ == '__main__':
    test()
