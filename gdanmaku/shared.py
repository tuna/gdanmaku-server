#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import re

RE_INVALID = re.compile(r'[\udc00-\udcff]')
# RE_NEWLINE = re.compile(ur'\\n')

DM_COLORS = {'blue', 'white', 'red', 'yellow', 'cyan', 'green', 'purple', 'black'}
DM_COLOR_TRANS = {
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
DM_POSITIONS = {'fly', 'top', 'bottom'}
DM_POSITION_TRANS = {'飞过': 'fly', '顶部': 'top', '底部': 'bottom'}

# vim: ts=4 sw=4 sts=4 expandtab
