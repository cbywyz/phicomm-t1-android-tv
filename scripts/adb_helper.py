#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通过 Home Assistant 的 androidtv 集成给盒子下发 adb 命令。

为什么不用本机 adb：
    T1 的 ro.adb.secure=0，本机 adb connect 会一直 offline（详见 docs/01）。

为什么带 nonce：
    HA 的 media_player 实体上 adb_response 属性存在「回显滞后」——
    读到的可能是上一条命令的输出，导致结果错位。所以每条命令前后各 echo 一个
    随机串，只有读到结束标记才算这条命令的结果。

用法：
    export HA_URL=http://192.168.1.10:8123
    export HA_TOKEN=xxxx
    python adb_helper.py "getprop ro.build.version.release"

    # 指定实体（默认自动挑第一个 media_player.android_tv_*）
    export TV_ENTITY=media_player.android_tv_192_168_1_20
"""
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ha_ws import connect  # noqa: E402

E = os.environ.get('TV_ENTITY') or ''

_ws = None


def ws():
    global _ws
    if _ws is None:
        _ws = connect()
    return _ws


def auto_entity():
    global E
    if E:
        return E
    states = ws().cmd({'type': 'get_states'}).get('result') or []
    cands = [s['entity_id'] for s in states
             if s['entity_id'].startswith('media_player.android_tv_')]
    if not cands:
        raise SystemExit('没找到 media_player.android_tv_* 实体，请设置 TV_ENTITY')
    if len(cands) > 1:
        # 家里有多台 androidtv 设备时不要瞎猜，猜错了命令会打到别的设备上
        raise SystemExit(
            '检测到多个 androidtv 实体，请用 TV_ENTITY 指定其中一个：\n  '
            + '\n  '.join(cands)
        )
    E = cands[0]
    print('[i] 使用实体:', E, file=sys.stderr)
    return E


def _attrs():
    eid = auto_entity()
    for s in ws().cmd({'type': 'get_states'})['result']:
        if s['entity_id'] == eid:
            return s['state'], s['attributes'].get('app_name'), s['attributes'].get('adb_response')
    return None, None, None


def adb(cmd, timeout=20, retry=3):
    """下发一条 adb 命令，返回设备回显（已剥离 nonce）。

    只有 **开始标记和结束标记都出现** 才算这条命令的结果。
    只看到结束标记 = 读到的是上一条命令的残留回显（HA 的 adb_response
    更新有延迟，连发命令时很常见），此时换个 nonce 重试。
    """
    eid = auto_entity()
    per_try = max(4.0, float(timeout) / max(1, retry))
    last = None
    for _ in range(max(1, retry)):
        nonce = 'NA%05d' % random.randint(0, 99999)
        full = 'echo %s_S; %s; echo %s_E' % (nonce, cmd, nonce)
        ws().call_service('androidtv', 'adb_command', {'command': full}, {'entity_id': eid})

        deadline = time.time() + per_try
        while time.time() < deadline:
            time.sleep(1.2)
            _, _, resp = _attrs()
            s = str(resp or '')
            last = s
            if (nonce + '_S') in s and (nonce + '_E') in s:
                body = s.split(nonce + '_S', 1)[-1].split(nonce + '_E', 1)[0]
                return body.strip()
    return '<TIMEOUT> last=%r' % (str(last)[-120:] if last else None)


def state():
    st, app, _ = _attrs()
    return st, app


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    for c in sys.argv[1:]:
        print('$', c)
        print(adb(c))
