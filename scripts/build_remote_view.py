#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成/更新「电视盒子遥控」Lovelace 视图。

默认（不加 --apply）只打印预览，不写 HA。
加 --apply 才写入，写入前自动备份现有 Lovelace 配置到本目录。

环境变量：
    HA_URL / HA_TOKEN
    TV_ENTITY        默认自动挑 media_player.android_tv_*
    DASHBOARD_PATH   仪表盘 url_path，默认 tv-remote
    VIEW_PATH        视图路径，默认 t1

自定义：
    下面的 APPS 列表改成你自己的包名/图标/文字。
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ha_ws import connect  # noqa: E402

TV_ENTITY = os.environ.get('TV_ENTITY', '')
DASHBOARD = os.environ.get('DASHBOARD_PATH', 'tv-remote')
VIEW_PATH = os.environ.get('VIEW_PATH', 't1')
KEYPAD_SWITCH = 'input_boolean.t1_keypad'
TEXT_ENTITY = 'input_text.t1_text'
HERE = os.path.dirname(os.path.abspath(__file__))

GREEN, RED, BLUE, PURPLE, GREY = '#43a047', '#e53935', '#1e88e5', '#8e24aa', '#78909c'
NAV = '#546e7a'

# name, icon, 显示文字, 命令, 颜色
APPS = [
    ('app_desktop', 'mdi:image-frame', 'Aerial',
     'am start -n app.orchard.tv/.MainActivity', BLUE),
    ('app_stock', 'mdi:chart-line', '同花顺',
     'am start -n com.hexin.plat.androidTV/.AndroidLogoActivity', RED),
]


def adb_action(cmd):
    return {
        'action': 'perform-action',
        'perform_action': 'androidtv.adb_command',
        'target': {'entity_id': TV_ENTITY},
        'data': {'command': cmd},
    }


def key(code):
    return adb_action('input keyevent %d' % code)


def btn(name, icon, label, action, color):
    return {
        'type': 'button', 'name': name, 'icon': icon, 'label': label,
        'styles': ':host {\n  --icon-color: %s;\n}' % color,
        'tap_action': action,
    }


def styles_of(items):
    return '\n'.join(
        '#%s::part(icon) { color: %s; }'
        % (a['name'], a['styles'].split('color: ')[1].rstrip(';\n} '))
        for a in items if a['type'] == 'button'
    )


def main_buttons():
    b = [
        btn('power', 'mdi:power', '电源', key(26), RED),
        btn('mute', 'mdi:volume-mute', '静音', key(164), GREY),
        btn('volume_up', 'mdi:volume-plus', '音量+', key(24), BLUE),
        btn('volume_down', 'mdi:volume-minus', '音量-', key(25), BLUE),
        btn('play_pause', 'mdi:play-pause', '播放', key(85), PURPLE),
        btn('stop', 'mdi:stop', '停止', key(86), RED),
        btn('previous', 'mdi:skip-previous', '上一个', key(88), GREY),
        btn('next', 'mdi:skip-next', '下一个', key(87), GREY),
        btn('rewind', 'mdi:rewind-10', '快退', key(89), GREY),
        btn('fast_forward', 'mdi:fast-forward-10', '快进', key(90), GREY),
        btn('back', 'mdi:keyboard-backspace', '返回', key(4), GREY),
        btn('home', 'mdi:home', '主页', key(3), GREEN),
        btn('menu', 'mdi:menu', '菜单', key(82), GREY),
        btn('settings', 'mdi:cog', '设置',
            adb_action('am start -n com.android.settings/.Settings'), GREY),
    ]
    for name, icon, label, cmd, color in APPS:
        b.append(btn(name, icon, label, adb_action(cmd), color))
    return b


def keypad_buttons():
    b = [btn('kp_%d' % d, 'mdi:numeric-%d' % d, '', key(d + 7), NAV) for d in range(1, 10)]
    clear = '; '.join(['input keyevent ' + ' '.join(['67'] * 10)] * 3)
    b += [
        btn('kp_dot', '', '.', key(56), GREY),
        btn('kp_0', 'mdi:numeric-0', '', key(7), NAV),
        btn('kp_del', 'mdi:backspace-outline', '删除', key(67), RED),
        btn('kp_clear', 'mdi:backspace-reverse-outline', '清空', adb_action(clear), RED),
        btn('kp_enter', 'mdi:keyboard-return', '确定', key(66), GREEN),
        btn('kp_space', 'mdi:keyboard-space', '空格', key(62), GREY),
    ]
    return b


def build_view():
    main_btns = main_buttons()
    kp_btns = keypad_buttons()

    remote = {
        'type': 'custom:universal-remote-card',
        'title': '遥控',
        'custom_actions': main_btns,
        'rows': [
            ['power', 'mute'] + [a[0] for a in APPS],
            ['volume_up', 'play_pause', 'volume_down'],
            ['dpad'],
            ['back', 'home', 'menu', 'settings'],
            ['previous', 'rewind', 'stop', 'fast_forward', 'next'],
        ],
        'styles': styles_of(main_btns + kp_btns),
    }

    keypad = {
        'type': 'custom:universal-remote-card',
        'title': '数字 / 文字输入',
        'custom_actions': kp_btns,
        'rows': [
            ['kp_1', 'kp_2', 'kp_3'],
            ['kp_4', 'kp_5', 'kp_6'],
            ['kp_7', 'kp_8', 'kp_9'],
            ['kp_dot', 'kp_0', 'kp_del'],
            ['kp_clear', 'kp_enter', 'kp_space'],
        ],
        'styles': styles_of(main_btns + kp_btns),
    }

    toggle = {
        'type': 'custom:mushroom-chips-card',
        'alignment': 'center',
        'chips': [{
            'type': 'template',
            'icon': "{{ 'mdi:chevron-up' if is_state('%s','on') else 'mdi:dialpad' }}" % KEYPAD_SWITCH,
            'content': "{{ '收起键盘' if is_state('%s','on') else '数字键盘 / 文字输入' }}" % KEYPAD_SWITCH,
            'tap_action': {
                'action': 'perform-action',
                'perform_action': 'input_boolean.toggle',
                'target': {'entity_id': KEYPAD_SWITCH},
            },
        }],
    }

    area = {
        'type': 'conditional',
        'conditions': [{'condition': 'state', 'entity': KEYPAD_SWITCH, 'state': 'on'}],
        'card': {
            'type': 'vertical-stack',
            'cards': [
                keypad,
                {
                    'type': 'entities',
                    'title': '发送文字到盒子（支持中文，光标要先在输入框里）',
                    'entities': [{'entity': TEXT_ENTITY, 'name': '输入后回车发送'}],
                },
            ],
        },
    }

    return {
        'title': '电视盒子',
        'path': VIEW_PATH,
        'icon': 'mdi:set-top-box',
        'cards': [{
            'type': 'vertical-stack',
            'cards': [
                {
                    'type': 'custom:mushroom-media-player-card',
                    'entity': TV_ENTITY,
                    'name': '电视盒子',
                    'use_media_info': False,
                    'show_volume_level': True,
                    'volume_controls': ['volume_buttons'],
                    'media_controls': ['on_off', 'play_pause', 'stop'],
                },
                remote,
                toggle,
                area,
            ],
        }],
    }


def main():
    global TV_ENTITY
    ws = connect()
    if not TV_ENTITY:
        states = ws.cmd({'type': 'get_states'}).get('result') or []
        cands = [s['entity_id'] for s in states
                 if s['entity_id'].startswith('media_player.android_tv_')]
        if not cands:
            raise SystemExit('没找到 androidtv 实体，请设置 TV_ENTITY')
        TV_ENTITY = cands[0]
        print('[i] 使用实体:', TV_ENTITY)

    cfg = ws.cmd({'type': 'lovelace/config', 'url_path': DASHBOARD}).get('result') or {}
    views = cfg.get('views', [])
    print('现有视图:', [v.get('path') for v in views])

    ts = time.strftime('%Y%m%d_%H%M%S')
    bak = os.path.join(HERE, '_lovelace_%s_backup_%s.json' % (DASHBOARD, ts))
    with open(bak, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=1)
    print('已备份 ->', bak)

    new_view = build_view()
    out = [v for v in views if v.get('path') != VIEW_PATH]
    out.append(new_view)
    cfg['views'] = out

    if '--apply' not in sys.argv:
        print('预览模式（加 --apply 才写入）')
        print('按键数:', len(main_buttons()) + len(keypad_buttons()))
        return

    r = ws.cmd({'type': 'lovelace/config/save', 'url_path': DASHBOARD, 'config': cfg})
    print('保存:', r.get('success'), r.get('error', ''))


if __name__ == '__main__':
    main()
