#!/usr/bin/env python2
# -*- coding:utf-8 -*-
import os

DEBUG = True

SECRET_KEY = '4285ee4ca33d4f34ba16f91def850914'
CSRF_ENABLED = True

SCRIPT_ROOT = ""

FILE_PATH = os.path.dirname(__file__)

DB_PATH = os.path.join(FILE_PATH, "db")
MEDIA_PATH = os.path.join(FILE_PATH, "media")

# DB
REDIS_HOST = 'redis'
REDIS_PORT = 6379
REDIS_DB = 1
REDIS_PREFIX = "gd_"

# WECHAT
WECHAT_TOKEN = ""

PERSISTENT_CHANNELS = [
    {'name': 'demo', 'desc': u"演示频道, 发布、订阅均无需密码"},
]

try:
    from settings_local import *
except:
    pass

# vim: ts=4 sw=4 sts=4 expandtab
