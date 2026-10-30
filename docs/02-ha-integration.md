# 02 接入 Home Assistant

## 添加 androidtv 集成

HA → 设置 → 设备与服务 → 添加集成 → 搜 `Android TV` → 填盒子 IP。

因为 T1 的 `ro.adb.secure=0`（见 [docs/01](01-device.md)），**不会弹电视上的配对码**，
连上就直接出实体。如果卡住，先手动确认端口：

```bash
adb connect 192.168.1.20:5555     # 只用来确认端口开着，不用它下发命令
```

> 💡 **为什么只走 HA、不动本机 adb**：T1 的 `ro.adb.secure=0` 让现代 adb host 连上后立刻 `offline`（见 [docs/01](01-device.md) 第 11 节），所以本机 `adb` 本就用不了；而 HA 的 androidtv 集成是纯 socket 实现的 adb 协议，能正常下命令。**另外记住 adbd 是单会话的**——任何能成功握手的 adb 客户端（电脑、脚本、别的集成）同一时刻只能有一个连着，多一个就会把 HA 挤掉。所以调试统一用 `adb_helper.py`（走 HA 通道，不占本机会话），别另起 adb 客户端。

集成成功后会有两个实体：

```
media_player.android_tv_192_168_1_20
remote.android_tv_192_168_1_20
```

实体 ID 里的点被替换成下划线，记住这个命名规则，后面所有脚本都用它。

---

## 把名字改成中文

默认实体名是 `Android TV 192.168.1.20`，在活动日志、面板里都很丑。改设备名即可：

```python
# 通过 WebSocket
ws.send({
    "type": "config/device_registry/update",
    "device_id": "<设备注册表里的 id>",
    "name_by_user": "斐讯 T1 盒子",
})
```

设备 id 怎么拿：

```python
ws.send({"type": "config/device_registry/list"}, callback=...)
```

在结果里找 `identifiers` 含 `androidtv` 的那条。

改完之后：

- `media_player.*` 的 friendly_name 立刻变「斐讯 T1 盒子」
- 活动（logbook）里显示的就是中文名，不再是「Android TV 192.168.1.20」

> 实体 ID 本身不会变，脚本里继续用 `media_player.android_tv_192_168_1_20` 就行。

---

## 让 T1 出现在活动页

如果你的活动页（`activity` 视图）用的是 logbook 卡 + `entities` 白名单，
白名单里要手动加上这个 `media_player`，否则它的一切动作都不会显示。

```yaml
type: logbook
entities:
  - media_player.xiaomi_tv
  - media_player.android_tv_192_168_1_20   # 加这一行
```

---

## 离线自愈（强烈建议）

盒子断电重启、或者路由器重启后，androidtv 集成经常**卡在 `unavailable` 不再自动恢复**，
必须手动「重新加载集成」。

加一条自动化，掉线满 10 分钟自动重载一次：

```yaml
- id: t1_box_reload_when_offline
  alias: "[T1盒子] 离线自动重载集成"
  mode: single
  max_exceeded: silent
  trigger:
    - platform: state
      entity_id: media_player.android_tv_192_168_1_20
      to: "unavailable"
      for:
        minutes: 10
  action:
    - service: homeassistant.reload_config_entry
      target:
        entity_id: media_player.android_tv_192_168_1_20
```

为什么是 10 分钟：盒子关机时也会变成 unavailable，如果只等 1 分钟就会不停重载，日志全是噪音。
10 分钟能覆盖「开机 + adb 起来」的时间，又不会因为临时断网误触发。

---

## 验证连通

```bash
python scripts/adb_helper.py "getprop ro.build.version.release"
# 7.1.2
```

能返回版本号，说明 HA → adb → 盒子的链路通了，可以开始做遥控面板。
