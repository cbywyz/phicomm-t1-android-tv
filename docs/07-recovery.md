# 07 自救手册

改之前先读一遍。出事了按场景查。

---

## 场景 1：adbd 被我停了 / 5555 连不上

**症状**：`adb connect` 超时，HA 里的实体变 unavailable。

**唯一解法：断电重启。**

```bash
adb shell "stop adbd; start adbd"    # 就是这条把端口关掉的
```

因为 `start adbd` 没有执行，端口不会自己回来。T1 上没有硬复位 adbd 的办法
（`setprop ctl.start adbd` 需要 init 权限，`su` 在工具箱域里也调不动）。

拔电 → 等 5 秒 → 插电。开机后 adb **约 15–18 秒**重新监听 5555。

---

## 场景 2：停错了系统包，进不去桌面

**症状**：开机停在黑屏 / 开机动画 / 桌面崩溃循环。

**解法：在 adb 抢上时间窗。**

1. 断电，重新开机
2. 开机后 **第 12 秒左右**开始不停尝试：

```bash
# 在 HA 上（或任何能 adb 的机器）
until adb connect 192.168.1.20:5555 2>/dev/null | grep -q connected; do sleep 1; done
adb shell pm enable <刚才停掉的包名>
adb reboot
```

3. 如果抢不上，多试几次；实在不行，考虑恢复出厂（会丢所有 App）

**能提前避免的**：

- 一次只停 2–3 个包，停完就重启验证
- 停之前把包名记在纸上：

```bash
adb shell pm list packages -d > /sdcard/disabled_before.txt
```

这样至少知道要恢复哪些。

---

## 场景 3：Lovelace 面板改坏了（打开就是报错/空白）

**关键：Lovelace 配置在 HA 里是可以通过 WebSocket 直接覆盖的，不需要能打开 UI。**

```python
from scripts.ha_ws import HAWS          # 见仓库里的极简客户端
ws = HAWS(HA_URL, HA_TOKEN)

cfg = json.load(open('_lovelace_backup_20261029_1148.json', encoding='utf-8'))
ws.send({'type': 'lovelace/config/save', 'url_path': 'tv-remote', 'config': cfg})
```

**前提是改之前备份过。** 本仓库的 `build_remote_view.py` 在写入前会自动把
现有配置 dump 到 `_lovelace_*_backup_<时间>.json`，别删这些文件。

如果连备份都没了：`lovelace/config` 读出来是整份 JSON，先读出来贴到本地文件里存一份，再手动删掉可疑卡片。

---

## 场景 4：automations.yaml 改坏，HA 起不来 / 自动化全红

**先看日志定位行号**：

```bash
tail -100 /config/home-assistant.log | grep -i -A3 error
```

**回滚**：仓库脚本每次写入前都会 `cp` 一份 `.bak-<时间戳>`：

```bash
ls -lt /config/automations.yaml.bak-* | head -3
cp /config/automations.yaml.bak-20261029_122833 /config/automations.yaml
```

然后：

- HA 能起 → 开发者工具 → 重新加载 YAML
- HA 起不来 → 重启 HA 容器

**验证 YAML 语法**（在能 SSH 到 HA 主机的机器上）：

```bash
docker exec homeassistant python -c "
import yaml,sys
yaml.safe_load(open('/config/automations.yaml'))
print('OK')
"
```

---

## 场景 5：输入法被我留在 ADBKeyboard 上了

**症状**：遥控器点进输入框，没有九宫格键盘了。

**解法**：

```bash
adb shell ime set com.sohu.inputmethod.sogou.tv/.SogouIME
adb shell settings get secure default_input_method
```

如果 adb 也不通，去 设置 → 系统 → 语言和输入法 → 当前输入法，改回搜狗。

**根因预防**：发送中文的自动化必须用 `mode: queued`，不能用 `restart`（见 [docs/06](06-pitfalls.md#13-自动化-mode-restart-会把输入法留在错的状态)）。

---

## 场景 6：遥控面板点下去没反应

按这个顺序排查，别跳步：

1. **集成活着吗**

```bash
python scripts/adb_helper.py "getprop ro.build.version.release"
```

超时 → 盒子关机 / adbd 没起 / 集成卡死（重载集成）

2. **命令能注入吗**

```bash
python scripts/adb_helper.py "dumpsys input | grep -A 4 RecentQueue"
```

按一下面板上的键，看有没有新的 `KeyEvent(... action=0 ...)`。
没有 → 命令没到；有 → 是 App 不吃这个键（比如某些页面不吃 MENU）。

3. **是不是键码选错了**

对照 [docs/03 的键码表](03-remote-panel.md#键码表全部实测通过) 逐个试。

---

## 一份最小应急清单

出问题先确认这三件事，90% 的情况能定位：

| 检查 | 命令 | 正常表现 |
|---|---|---|
| 盒子在线 | `ping 192.168.1.20` | 通 |
| adb 在听 | `nc -z 192.168.1.20 5555` | 端口开 |
| HA 能下命令 | `adb_helper.py "echo ok"` | `ok` |
