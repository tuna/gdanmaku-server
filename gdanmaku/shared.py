#!/usr/bin/env python2
# -*- coding:utf-8 -*-
import re

RE_INVALID = re.compile(ur'[\udc00-\udcff]')
# RE_NEWLINE = re.compile(ur'\\n')

DM_COLORS = {'blue', 'white', 'red', 'yellow', 'cyan', 'green', 'purple', 'black'}
DM_COLOR_TRANS = {
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
DM_POSITIONS = {'fly', 'top', 'bottom'}
DM_POSITION_TRANS = {u'飞过': 'fly', u'顶部': 'top', u'底部': 'bottom'}

# vim: ts=4 sw=4 sts=4 expandtab
