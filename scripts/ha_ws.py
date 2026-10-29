#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""极简 Home Assistant WebSocket 客户端（零依赖，只用标准库）。

用法：
    from ha_ws import connect
    ws = connect()                       # 读环境变量 HA_URL / HA_TOKEN
    r = ws.cmd({"type": "config/entity_registry/list"})
    print(len(r["result"]))
    ws.close()

环境变量：
    HA_URL    如 http://192.168.1.10:8123
    HA_TOKEN  HA 里的「长期访问令牌」（左下角头像 → 安全 → 长期访问令牌）

为什么不用现成的库：这个脚本要能在一台什么都没装的机器上直接跑，
而且只用到 cmd()（发一条命令、等它的 result），150 行就够了。
"""
import base64
import json
import os
import socket
import struct
import urllib.parse

for _k in ('http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'all_proxy', 'ALL_PROXY'):
    os.environ.pop(_k, None)
os.environ.setdefault('no_proxy', '*')


class HAWS:
    """最小可用 HA WebSocket 客户端（处理了 TCP 粘包 / 分帧 / 大消息）。"""

    def __init__(self, host, port, token, timeout=30):
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.buf = b''
        key = base64.b64encode(os.urandom(16)).decode()
        req = (
            'GET /api/websocket HTTP/1.1\r\nHost: %s:%d\r\n'
            'Upgrade: websocket\r\nConnection: Upgrade\r\n'
            'Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n'
        ) % (host, port, key)
        self.sock.sendall(req.encode())
        head = b''
        while b'\r\n\r\n' not in head:
            head += self.sock.recv(4096)
        self.buf = head.split(b'\r\n\r\n', 1)[1]

        first = self.recv_msg()
        if first.get('type') != 'auth_required':
            raise ConnectionError('不是 HA WebSocket 服务: %r' % first)

        self._id = 0
        # auth 的响应是 {"type":"auth_ok"}，不带 id，不能走 cmd()
        self._send_frame(json.dumps({'type': 'auth', 'access_token': token}).encode('utf-8'))
        while True:
            m = self.recv_msg()
            t = m.get('type')
            if t == 'auth_ok':
                break
            if t == 'auth_invalid':
                raise PermissionError('HA 认证失败: %s' % m.get('message'))

    # ---------- 底层帧 ----------
    def _read_exact(self, n):
        while len(self.buf) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError('连接已断开')
            self.buf += chunk
        r, self.buf = self.buf[:n], self.buf[n:]
        return r

    def _send_frame(self, payload, opcode=0x1):
        mask = os.urandom(4)
        hdr = bytes([0x80 | opcode])
        L = len(payload)
        if L < 126:
            hdr += bytes([0x80 | L])
        elif L < 65536:
            hdr += bytes([0x80 | 126]) + struct.pack('>H', L)
        else:
            hdr += bytes([0x80 | 127]) + struct.pack('>Q', L)
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        self.sock.sendall(hdr + mask + masked)

    def recv_msg(self):
        data = b''
        while True:
            h = self._read_exact(2)
            opcode = h[0] & 0x0F
            fin = bool(h[0] & 0x80)
            masked = bool(h[1] & 0x80)
            L = h[1] & 0x7F
            if L == 126:
                L = struct.unpack('>H', self._read_exact(2))[0]
            elif L == 127:
                L = struct.unpack('>Q', self._read_exact(8))[0]
            mask = self._read_exact(4) if masked else None
            payload = self._read_exact(L)
            if mask:
                payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
            if opcode == 0x8:
                raise ConnectionError('服务端关闭连接')
            if opcode == 0x9:
                self._send_frame(payload, opcode=0xA)
                continue
            if opcode == 0xA:
                continue
            data += payload
            if fin:
                break
        return json.loads(data.decode('utf-8'))

    # ---------- 应用层 ----------
    def cmd(self, obj):
        """发一条命令，返回带 result 的完整消息。"""
        self._id += 1
        obj = dict(obj)
        obj['id'] = self._id
        self._send_frame(json.dumps(obj).encode('utf-8'))
        while True:
            m = self.recv_msg()
            if m.get('id') == self._id and m.get('type') == 'result':
                return m

    def call_service(self, domain, service, data=None, target=None):
        return self.cmd({
            'type': 'call_service',
            'domain': domain,
            'service': service,
            'service_data': data or {},
            'target': target or {},
        })

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass


def connect(url=None, token=None, timeout=30):
    """从 HA_URL / HA_TOKEN 环境变量建立连接。"""
    url = url or os.environ.get('HA_URL', 'http://homeassistant.local:8123')
    token = token or os.environ.get('HA_TOKEN')
    if not token:
        raise SystemExit('缺少 HA_TOKEN 环境变量（HA 头像 → 安全 → 长期访问令牌）')
    u = urllib.parse.urlparse(url if '//' in url else 'http://' + url)
    host = u.hostname or 'homeassistant.local'
    port = u.port or 8123
    return HAWS(host, port, token, timeout=timeout)


if __name__ == '__main__':
    ws = connect()
    r = ws.cmd({'type': 'config/entity_registry/list'})
    print('实体总数:', len(r.get('result', [])))
    ws.close()
