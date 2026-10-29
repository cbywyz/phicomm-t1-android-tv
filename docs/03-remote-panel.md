# 03 遥控面板

面板用 HACS 里的 **Universal Remote Card（URC）**，一张卡就能画完整个遥控器，
按钮全部走 `androidtv.adb_command` + `input keyevent`。

---

## 最重要的一条：`remote.send_command` 在这台盒子上不可靠

先把结论放前面：

> **`remote.send_command` 的 `DPAD_UP / DPAD_DOWN / DPAD_LEFT / DPAD_RIGHT / DPAD_CENTER`
> 在这台盒子上根本不注入**，只有 BACK / HOME / MENU / 音量这几个会生效。

所以面板里**所有**按键统一走：

```yaml
action: perform-action
perform_action: androidtv.adb_command
target:
  entity_id: media_player.android_tv_192_168_1_20
data:
  command: input keyevent 19
```

---

## 怎么确认键真的按下去了（不要用截图）

第一版我用截图对比来判断，结果被 Aerial 桌面骗了——**它的时钟每秒刷新**，
两张截图 md5 必然不同，看起来「按了有反应」，其实什么都没发生。

正确的是看输入事件队列：

```bash
adb shell dumpsys input | grep -A 14 RecentQueue
```

```
KeyEvent(... action=0, keyCode=19 ...)   # 按下
KeyEvent(... action=1, keyCode=19 ...)   # 抬起
```

有这一对才叫真注入了。用 `adb_helper.py` 跑：

```bash
python scripts/adb_helper.py "dumpsys input | grep -A 14 RecentQueue"
```

---

## 键码表（全部实测通过）

| 功能 | keyevent | 功能 | keyevent |
|---|---|---|---|
| 电源 | 26 | 返回 | 4 |
| 音量 + | 24 | 主页 | 3 |
| 音量 - | 25 | 菜单 | 82 |
| 静音 | 164 | 方向 上 | 19 |
| 播放 / 暂停 | 85 | 方向 下 | 20 |
| 停止 | 86 | 方向 左 | 21 |
| 上一个 | 88 | 方向 右 | 22 |
| 下一个 | 87 | 确定 | 23 |
| 快退 | 89 | 删除（退格） | 67 |
| 快进 | 90 | 回车 / 确定 | 66 |
| 数字 0 | 7 | 空格 | 62 |
| 数字 1–9 | 8–16 | 小数点 | 56 |

---

## 卡片结构

```yaml
type: custom:universal-remote-card
title: 遥控
custom_actions:
  - type: button
    name: power
    icon: mdi:power
    label: 电源
    styles: |
      :host {
        --icon-color: #e53935;
      }
    tap_action:
      action: perform-action
      perform_action: androidtv.adb_command
      target: { entity_id: media_player.android_tv_192_168_1_20 }
      data: { command: "input keyevent 26" }
rows:
  - [power, mute, app_home, app_stock]
  - [volume_up, play_pause, volume_down]
  - [dpad]                                  # URC 内置圆盘，一次画完方向键+确定
  - [back, home, menu, settings]
  - [previous, rewind, stop, fast_forward, next]
```

要点：

- `name` 是内部标识，`rows` 里靠它引用，不显示
- `label` 空字符串时只显示图标；数字键适合这样，图标本身已经是数字
- 颜色写 `styles` 里的 `--icon-color`
- `[dpad]` 是 URC 的特殊行，自带四向 + 中间确定，比手画 5 个按钮好看

生成整个面板用 [`scripts/build_remote_view.py`](../scripts/build_remote_view.py)，
改完 `--apply` 才写入 HA，写入前自动备份 Lovelace 配置。

---

## 音量滑条别做

`media_player.volume_set` 在这台盒子上**不生效**：设 0.34，实际还是 0.7333，
而且不会同步回 HA。不要浪费时间去调，直接用 `keyevent 24 / 25`。

`mushroom-media-player-card` 里也把 `volume_controls` 设成 `volume_buttons`，别用滑条。

---

## 启动 App

两种命令，哪个通用用哪个：

```bash
# A. 指定 Activity（精确，但要知道类名）
am start -n app.orchard.tv/.MainActivity

# B. monkey 拉起 LAUNCHER（对自定义 ROM 的壳更稳，推荐）
monkey -p com.fxrom.launcher.tvlive -c android.intent.category.LAUNCHER 1
```

拿包名和入口：

```bash
adb shell pm list packages -3
adb shell dumpsys package com.hexin.plat.androidTV | grep -A2 "android.intent.action.MAIN"
```

T1 上验证可用的：

| App | 命令 |
|---|---|
| Aerial 桌面 | `am start -n app.orchard.tv/.MainActivity` |
| 同花顺 | `am start -n com.hexin.plat.androidTV/.AndroidLogoActivity` |
| 斐讯直播 | `monkey -p com.fxrom.launcher.tvlive -c android.intent.category.LAUNCHER 1` |
| 斐讯影音 | `monkey -p com.fxrom.launcher.media -c android.intent.category.LAUNCHER 1` |
| 系统设置 | `am start -n com.android.settings/.Settings` |

---

## 下一步：接进来之后做什么

遥控面板是「底座」——盒子已经在 HA 里了，后面的玩法都是复用这个 `media_player` 实体。

最常接的一篇是同系列的 [**ha-tv-kids-lock**](https://github.com/cbywyz/ha-tv-kids-lock)：
不需要改电视、不需要装电视端 App，全部在 HA 侧做，孩子拿遥控器绕不过去。

| 能力 | 怎么做 |
|---|---|
| 音量上限锁 | 监听 `media_player` 音量，超过阈值就 `volume_down` 打回去 |
| 信号源锁 | 检测到切到游戏机/HMDI 就切回来 |
| 每日观看配额 | 累计 `playing` 时长，到点自动关 |
| 倒计时暂停 | 定时器到点 → 暂停 + 提示 |

它用的就是你这里做出来的 `media_player.android_tv_*` 和 `remote.*`，实体名对上就能直接套。
