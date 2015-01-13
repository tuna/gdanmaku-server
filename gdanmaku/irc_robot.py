#!/usr/bin/env python2
# -*- coding:utf-8 -*-
from gevent import socket, spawn
from time import time, sleep
import string
import re


class IRCManager(object):

    def __init__(self, app, chan_mgr):
        self.app = app
        self.cm = chan_mgr
        self.bot_list = {}

    def connect_channel(self, dm_chan, irc_chan):
        self.bot_list[dm_chan] = IRCbot()
        self.bot_list[dm_chan].HOST = "card.freenode.net"
        self.bot_list[dm_chan].PORT = 6666
        self.bot_list[dm_chan].channel = irc_chan
        self.bot_list[dm_chan].method = "CHANNEL"
        self.bot_list[dm_chan].dmch = self.cm.get_channel(dm_chan)
        self.bot_list[dm_chan].manager = self
        if self.bot_list[dm_chan].check():
            spawn(self.bot_list[dm_chan].run)


class IRCbot(object):
    def __init__(self):
        self.HOST = None
        self.PORT = None
        self.NICK = "dmbot_"
        self.IDENT= "dmbot_"
        self.REALNAME="DANMAKU"
        self.channel = None
        self.timeout = 180
        self.dmch = None
        self.dmpw = None
        self.pingout = 5
        self.thread_stop = True
        self.ss = socket.socket()
        self.checked = False
        self.method = "MSG"  # CHANNEL OR MSG
        self.online = False
        self.manager = None

    def run(self):  # Overwrite run() method, put what you want the thread do here
        if not self.checked or not self.online:
            return None
        if not self.manager:
            return None

        logger = self.manager.app.logger
        last_ping = time()

        last_buf = ''
        while 1:
            # 判断是否存活
            pinging = False
            if time()-last_ping > self.timeout:
                self.ss.send("PING :TIMEOUTCHECK\r\n")
                pinging = True
            # 获得buffer并分离buffer的每一行

            buf = self.ss.recv(1024)
            lines = (last_buf + buf).split('\r\n')
            last_buf = '' if buf.endswith('\r\n') else lines.pop()

            # readbuffer = self.ss.recv(1024)
            # temp = string.split(readbuffer, "\n")
            # readbuffer = temp.pop()

            # 对每一行处理
            rspace = re.compile(r'\s+')
            for line in lines:
                if not line:
                    continue

                if line[0] == ':':
                    prefix, line = rspace.split(line, 1)
                    nick = prefix.split('!')[0]
                else:
                    nick = None

                cmd, params = rspace.split(line, 1)

                if cmd == 'PING':
                    self.ss.send("PONG " + params + '\r\n')
                    pinging = False
                    last_ping = time()

                elif cmd == 'PONG':
                    pinging = False
                    last_ping = time()

                elif cmd == 'JOIN':
                    logger.info("joined channel %s" % params)
                    if not params == self.channel:
                        self.online = False

                elif cmd == 'PRIVMSG':
                    targets, content = rspace.split(params, 1)

                    if not content[0] == ':':
                        continue

                    content = content[1:]

                    for target in targets.split(','):
                        if target[0] == '#':
                            if self.method == 'CHANNEL':
                                if self.shoot(content):
                                    self.ss.send(' '.join([
                                        "PRIVMSG",
                                        nick,
                                        'Shoot!\r\n',
                                    ]))
                                else:
                                    self.ss.send(' '.join([
                                        "PRIVMSG",
                                        targets,
                                        'Server Error\r\n',
                                    ]))
                            else:
                                self.ss.send(' '.join([
                                    'PRIVMSG',
                                    targets,
                                    'Please msg me in private\r\n',
                                ]))
                        else:
                            if self.shoot(content):
                                self.ss.send(' '.join([
                                    "PRIVMSG",
                                    nick,
                                    'Shoot!\r\n',
                                ]))
                            else:
                                self.ss.send(' '.join([
                                    "PRIVMSG",
                                    nick,
                                    'Server Error\r\n',
                                ]))

                else:
                    # Other commands
                    continue

            if pinging is True:
                if(time() - last_ping > (self.timeout + self.pingout)):
                    # print "TimeOut,Stop"
                    self.stop()

    def shoot(self, content):
        if not self.dmch.is_open:
            key = self.dmpw
            if key is None or (not self.dmch.verify_pub_passwd(key)):
                return False

        danmaku = {
            "text": content,
            "style": "white",
            "position": "fly"
        }
        self.dmch.new_danmaku(danmaku)
        return True

    def check(self):
        if self.HOST is None or self.PORT is None or self.dmch is None:
            return False

        self.ss.connect((self.HOST, self.PORT))
        self.ss.send("NICK %s\r\n" % self.NICK)
        self.ss.send("USER %s %s * :%s\r\n" % (self.IDENT, self.HOST, self.REALNAME))

        if self.channel is None:
            self.method = "MSG"
        else:
            self.ss.send("JOIN %s\r\n" % self.channel)
            # self.ss.send("PRIVMSG %s Hello\r\n" % self.channel)

        self.checked = True
        self.online = True
        return True

    def stop(self):
        self.thread_stop = True
        self.ss.send("QUIT")
        self.ss.close()
        self.online = False
        self.checked = False


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
