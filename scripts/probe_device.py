#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一条命令采集盒子的硬件 / 固件 / root / 网络 / 应用信息，打印成一份可贴的报告。

用途：
    1. 对照 docs/01 确认你的机器是不是同一套环境（同固件、同 root 状态）
    2. 提 issue 时直接贴报告，省掉来回问「你什么系统」

用法：
    export HA_URL=http://192.168.1.10:8123
    export HA_TOKEN=xxxx
    export TV_ENTITY=media_player.android_tv_192_168_1_20   # 可选，家里只有一台可省
    python probe_device.py

    # 存成文件方便贴
    python probe_device.py > my-box.txt
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from adb_helper import adb, auto_entity  # noqa: E402

# (标题, shell 命令, 备注)
PROBES = [
    ('品牌 / 型号 / 代号',
     'getprop ro.product.manufacturer; getprop ro.product.model; getprop ro.product.device', ''),

    ('固件版本号',
     'getprop ro.build.display.id; getprop ro.phicomm.inner.version; getprop ro.phicomm.outer.version', ''),

    ('Android 版本',
     'getprop ro.build.version.release; getprop ro.build.version.sdk', ''),

    ('构建指纹',
     'getprop ro.build.fingerprint; getprop ro.bootimage.build.fingerprint', ''),

    ('构建时间 / 类型',
     'getprop ro.build.date; getprop ro.build.type; getprop ro.build.tags', ''),

    ('平台 / 架构',
     'getprop ro.board.platform; getprop ro.hardware; getprop ro.product.cpu.abi; getprop ro.product.cpu.abilist', ''),

    ('CPU 核数',
     'grep -c ^processor /proc/cpuinfo', ''),

    ('内核',
     'cat /proc/version', ''),

    ('内存',
     'head -3 /proc/meminfo; free -m', ''),

    ('存储',
     'df -h /data /system', ''),

    ('显示',
     'wm size; wm density', ''),

    ('安全状态',
     'getenforce; getprop ro.secure; getprop ro.adb.secure; getprop ro.debuggable', ''),

    ('root 状态',
     'which su; su --version 2>&1 | head -1; su -c id 2>&1 | head -1; getprop ro.romhelper.root', ''),

    ('有没有自定义 recovery',
     'ls /system/bin/install-recovery.sh 2>&1; ls -d /system/su.d 2>&1', ''),

    ('输入法',
     'settings get secure default_input_method; ime list -s', ''),

    ('ADB 端口',
     'getprop persist.adb.tcp.port; getprop service.adb.tcp.port', ''),

    ('网络',
     'ip addr show wlan0 2>/dev/null | grep -E "inet |link/ether"; '
     'ip addr show eth0 2>/dev/null | grep -E "inet |link/ether"', ''),

    ('系统预装 App',
     'ls /system/app', ''),

    ('第三方 App',
     'pm list packages -3', ''),

    ('已停用的 App',
     'pm list packages -d', ''),

    ('可用工具',
     'which wget curl busybox; su -c "id" 2>&1 | head -1', ''),

    ('运行状态',
     'uptime; dumpsys window | grep mCurrentFocus', ''),
]


def main():
    eid = auto_entity()
    print('=' * 62)
    print(' 盒子环境探测报告')
    print(' 实体: %s' % eid)
    print('=' * 62)

    for title, cmd, _note in PROBES:
        print('\n### %s' % title)
        out = adb(cmd, timeout=40)
        if not out or out.startswith('<TIMEOUT>'):
            print('  (读取失败: %s)' % (out or '空'))
            continue
        for line in out.splitlines():
            if line.strip():
                print('  ' + line)

    print('\n' + '=' * 62)
    print(' 对照 docs/01 看这几行：')
    print('   ro.build.display.id  → 固件是不是 T1_ROM_20211231')
    print('   ro.board.platform    → 是不是 gxm（Amlogic）')
    print('   su -c id 的 context  → 是不是 u:r:toolbox:s0（残缺 root）')
    print('=' * 62)


if __name__ == '__main__':
    main()
