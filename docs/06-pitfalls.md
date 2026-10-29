# 06 踩坑清单

按杀伤力排序。每条都是真踩过的，含错误现场。

---

## 1. `stop adbd` 会把你关在门外（最危险）

```bash
adb shell "stop adbd; start adbd"     # ☠️ 千万不要
```

**现场**：命令发出后 adb 立刻断开，`start adbd` 永远没执行，5555 端口关闭，
只能跑去拔电源。

**原因**：`stop adbd` 杀掉的是「你正在里面跑命令的那个 shell 的宿主进程」。
shell 跟着一起死，后面的命令根本没机会执行。

**为什么不能指望自动拉起**：init.rc 里 adbd 虽然属于 `class core`（非 oneshot，理论上崩了会 respawn），
但 `stop` 是主动停止，不算崩溃，不会触发 respawn。

**正确做法**：想测重连，就在路由器/别的机器上断网再恢复，或者直接重启盒子。别 stop adbd。

---

## 2. `remote.send_command` 的方向键不注入

```yaml
service: remote.send_command
data:
  command: DPAD_UP        # ❌ 没反应，但也不报错
```

**现场**：日志显示调用成功，`last_triggered` 也更新了，就是电视上没动。

**实测结论**：这台盒子上只有 BACK / HOME / MENU / 音量 生效，`DPAD_*` 全部无效。

**解决**：统一改 `androidtv.adb_command` + `input keyevent 19/20/21/22/23`。

---

## 3. 用截图 md5 判断按键有没有生效 → 全是误判

**现场**：按方向键，截图 md5 变了，以为成功；其实桌面时钟每秒刷新，md5 必然变。

**解决**：看 `dumpsys input | grep -A14 RecentQueue` 里的 KeyEvent 对（action=0/1）。

---

## 4. `media_player.volume_set` 静默失败

**现场**：设 0.34，读回来还是 0.7333，不报错。

**解决**：删掉音量滑条，只用 `keyevent 24 / 25`。面板的 `volume_controls` 也设成 `volume_buttons`。

---

## 5. 往 `/system` 塞看门狗，两条路都被 SELinux 挡死

想给 adbd 加自启看门狗，试了两条路：

| 路径 | 结果 |
|---|---|
| `/system/su.d/99xxx.sh` | 不执行（SuperSU 的这个目录在某些版本根本不扫描） |
| `/system/bin/install-recovery.sh` | `init: Service 'flash_recovery' ... does not have a SELinux domain defined` |

**原因**：SELinux 是 enforcing，`su` 也被限制在 `u:r:toolbox:s0`，改不动 init 的服务上下文。

**结局**：删掉这两个文件，`mount -o remount,ro /system` 恢复，改用 HA 侧的离线自愈自动化
（见 [docs/02](02-ha-integration.md#离线自愈强烈建议)）。

**教训**：盒子端能做的有限，**把自愈逻辑放到 HA 侧**成本低得多。

---

## 6. Python `%` 格式化把 Jinja 的 `%}` 吃掉了

```python
card = {'primary': "{% if x %}A{% endif %}" % E}     # ❌ ValueError / 输出错乱
```

**原因**：Jinja 里的 `%}` 被 Python 当成格式化占位符。

**解决**：用 `.replace('__E__', entity_id)` 代替 `%`。

---

## 7. `tile` 卡的 `text-input` feature 不支持

**现场**：`Unknown type encountered: text-input`，整张卡渲染失败。

**解决**：用 `entities` 卡 + `input_text` 实体，或者在弹窗里放 `entities`。

---

## 8. `input_text/create` 的 `object_id` 不是合法字段

```json
{"type": "input_text/create", "name": "T1 数字键盘", "object_id": "t1_keypad"}
→ invalid_format: not a valid option at 'object_id'
```

**解决**：不给 `object_id`，实体 ID 由 `name` 自动生成（中文名会转成拼音）。
想要短 ID 就把 name 写短。

---

## 9. WS `render_template` 返回 `null`

```python
ws.send({"type": "render_template", "template": "{{ 1+1 }}"})   # result: null
```

**解决**：用 REST：

```bash
curl -s -X POST http://HA:8123/api/template \
  -H "Authorization: Bearer $HA_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"template": "{{ 1+1 }}"}'
```

调试模板（比如确认 `base64_encode`、`regex_findall` 存不存在）全靠它。

---

## 10. 盒子 wget 打 HA 的 8123 端口失败

```bash
wget -O /data/local/tmp/a.apk http://192.168.1.10:8123/local/a.apk
# wget: error getting response
```

ping 是通的，端口也是开的（浏览器能访问）。

**解决**：把文件放到任意 **80 端口** 的静态服务上（路由器 `/www`、`python -m http.server 80`），
立刻就能下。别在 8123 上耗。

---

## 11. 中文「打不进去」的第一嫌疑不是通道

**现场**：广播 `zzz`，输入框里只多了 `z`，以为 ADBKeyboard 有问题。

**真相**：那个输入框（同花顺股票代码框）**maxLength = 6**，里面已经有 5 个字符。

**教训**：测通道先用一个不限长的输入框（搜狗设置、登录页的密码框），别用业务输入框。

---

## 12. 「清空」写成 `while` 循环会挂死通道

```bash
i=0; while [ $i -lt 20 ]; do input keyevent 67; i=$((i+1)); done
# 实测 41 秒才返回，adb 通道超时
```

**解决**：一条命令带多个 keycode：

```bash
input keyevent 67 67 67 67 67 67 67 67 67 67
```

---

## 13. 自动化 `mode: restart` 会把输入法留在错的状态

发送中文的流程是「切走 IME → 广播 → 切回 IME」。如果用 `restart`，
连着发两条时第一条会被打断在中间，**输入法就永远停在 ADBKeyboard**，
家里人用遥控器就再也打不出字了。

**解决**：`mode: queued`。

---

## 14. Playwright 点 mushroom 卡被背景层拦截

**现场**：`element is not clickable, another element would receive the click`

**解决**：`locator.click(force=True)`。

---

## 15. 本机 `adb connect` 恒 offline，且不弹授权窗

见 [docs/01](01-device.md#为什么本机-adb-connect-一直-offline)。结论：别在本机折腾，走 HA。
