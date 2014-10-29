#!/usr/bin/env python2
# -*- coding:utf-8 -*-
import os

DEBUG = True

SECRET_KEY = '4285ee4ca33d4f34ba16f91def850914'
CSRF_ENABLED = True

SCRIPT_ROOT = ""

QBOX_NAME = "thunics"

FILE_PATH = os.path.dirname(__file__)

DB_PATH = os.path.join(FILE_PATH, "db")
MEDIA_PATH = os.path.join(FILE_PATH, "media")

# DB
SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(FILE_PATH, "gdanmaku.sqlite")


# vim: ts=4 sw=4 sts=4 expandtab
