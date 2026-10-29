# 04 数字键盘与中文输入

这是整套方案里最折腾、也最有用的一部分。

---

## 先说结论

| 输入内容 | 走哪条路 | 耗时 |
|---|---|---|
| 纯英文 / 数字 / 符号 | `adb shell input text '...'` | 快，不切输入法 |
| **含中文** | 临时切 ADBKeyboard → `am broadcast -a ADB_INPUT_B64` → 切回搜狗 | 约 2–3 秒 |

**为什么不能直接 `input text 中文`**：`input text` 走的是 `KeyCharacterMap`，
底层只映射 ASCII 可打印字符。汉字没有对应 keycode，塞进去就是空白或报错。

---

## 一、把数字键盘折叠起来

10 个数字键铺在遥控面板上，整个面板会变得很长。做法是：

1. 建一个 `input_boolean` 当开关
2. 主面板只留一个小胶囊
3. 键盘本体塞进 `conditional` 卡

```yaml
# 开关（也可以用 UI 里的「辅助元素」建）
# entity: input_boolean.t1_keypad
- type: custom:mushroom-chips-card
  alignment: center
  chips:
    - type: template
      icon: "{{ 'mdi:chevron-up' if is_state('input_boolean.t1_keypad','on') else 'mdi:dialpad' }}"
      content: "{{ '收起键盘' if is_state('input_boolean.t1_keypad','on') else '数字键盘 / 文字输入' }}"
      tap_action:
        action: perform-action
        perform_action: input_boolean.toggle
        target: { entity_id: input_boolean.t1_keypad }

- type: conditional
  conditions:
    - condition: state
      entity_id: input_boolean.t1_keypad
      state: "on"
  card:
    type: vertical-stack
    cards:
      - !include 你的数字键盘卡
      - !include 你的文字输入卡
```

键盘布局（5 行，含三个救命键）：

```
1  2  3
4  5  6
7  8  9
.  0  ⌫ 删除
清空 ⏎ 确定  ␣ 空格
```

### 「删除」和「清空」怎么实现

| 键 | 命令 | 说明 |
|---|---|---|
| 删除 | `input keyevent 67` | KEYCODE_DEL，删一位 |
| 清空 | `input keyevent 67 67 ...`（30 个，分 3 段） | 等价于狂按退格 |
| 确定 | `input keyevent 66` | KEYCODE_ENTER，提交搜索 |
| 空格 | `input keyevent 62` | 多词搜索 |
| 小数点 | `input keyevent 56` | 频道号 12.1 / 版本号 / IP |

「清空」的正确写法：

```bash
input keyevent 67 67 67 67 67 67 67 67 67 67; \
input keyevent 67 67 67 67 67 67 67 67 67 67; \
input keyevent 67 67 67 67 67 67 67 67 67 67
```

> ⚠️ **不要写成 `while` 循环**：
> ```bash
> i=0; while [ $i -lt 20 ]; do input keyevent 67; i=$((i+1)); done
> ```
> 实测跑 **41 秒还没返回**（每次 `input` 都要起一个新进程，盒子上极慢），
> 直接把 adb 通道超时挂死。多参数一条命令是最快的。

---

## 二、安装 ADBKeyboard

[ADBKeyboard](https://github.com/senzhk/ADBKeyBoard) 是一个 17 KB 的输入法，
没有界面，只监听广播，收到就把文字 commit 到当前输入框。支持 Unicode（所以支持中文）。

### 1. 把 APK 弄进盒子

盒子自带 busybox wget，但**不支持 https**，只能走内网 HTTP 中转。

```bash
# 电脑上先下好
curl -LO https://raw.githubusercontent.com/senzhk/ADBKeyBoard/master/ADBKeyboard.apk

# 丢到一个能被盒子 HTTP 访问的地方（路由器 / NAS / 电脑起 http.server 都行）
scp ADBKeyboard.apk root@192.168.1.1:/www/adbkb.apk
```

盒子上下载并安装：

```bash
wget -O /data/local/tmp/adbkb.apk http://192.168.1.1/adbkb.apk
pm install -r /data/local/tmp/adbkb.apk
# Success
pm list packages | grep adbkeyboard
# package:com.android.adbkeyboard
```

> ⚠️ **坑**：如果中转服务开在 HA 的 8123 端口，盒子 wget 会报
> `wget: error getting response`。换成路由器/任意 80 端口的静态文件服务就正常。
> 原因没深究，但换端口能解决。

脚本：[`scripts/install_adbkeyboard.sh`](../scripts/install_adbkeyboard.sh)

### 2. 启用，但**绝对不要设为默认**

```bash
ime enable com.android.adbkeyboard/.AdbIME
ime list -s
# com.sohu.inputmethod.sogou.tv/.SogouIME     ← 默认还是它
# com.android.adbkeyboard/.AdbIME             ← 已启用
```

**为什么不能 `ime set` 成默认**：盒子默认的搜狗 TV 输入法是给遥控器用的九宫格，
一旦把 ADBKeyboard 设成默认，遥控器在输入框里就没有键盘了 —— 家里人就彻底不会打字了。

正确做法是**发送时临时切，发完立刻切回**。

---

## 三、发一条中文

```bash
ime set com.android.adbkeyboard/.AdbIME
sleep 1
am broadcast -a ADB_INPUT_B64 --es msg '5Lit5paH'     # base64 的「中文」
sleep 1
ime set com.sohu.inputmethod.sogou.tv/.SogouIME
```

### 为什么用 `ADB_INPUT_B64` 而不是 `ADB_INPUT_TEXT`

`ADB_INPUT_TEXT` 要把原文塞进 shell 参数，中文、空格、单引号、换行都要自己转义，
一不小心就被 shell 吃掉。base64 之后只剩 `A-Za-z0-9+/=`，永远安全。

HA 模板里现成的过滤器：

```jinja
{{ '贵州茅台' | base64_encode }}      → 6LS15bee6IyF5Y+w
```

所以整条命令可以直接拼：

```jinja
ime set com.android.adbkeyboard/.AdbIME; sleep 1;
am broadcast -a ADB_INPUT_B64 --es msg '{{ txt | base64_encode }}'; sleep 1;
ime set com.sohu.inputmethod.sogou.tv/.SogouIME
```

---

## 四、完整自动化

见 [`scripts/send_text_automation.yaml`](../scripts/send_text_automation.yaml)，核心逻辑：

```jinja
{% if 文本里含非 ASCII 字符 %}
  临时切 IME → base64 广播 → 切回搜狗
{% else %}
  input text '...'
{% endif %}
```

判断是否含中文：

```jinja
{{ (txt or '') | regex_findall('[^ -~]') | count > 0 }}
```

`[^ -~]` 表示「不在 ASCII 可打印范围（0x20–0x7E）内的字符」，汉字、emoji 都会命中。

完整的自动化：

```yaml
- id: t1_box_send_text
  alias: "[T1盒子] 发送文字到盒子"
  mode: queued          # 关键：不要用 restart
  max: 4
  trigger:
    - platform: state
      entity_id: input_text.t1_shu_ru_wen_zi
  condition:
    - condition: template
      value_template: "{{ (trigger.to_state.state or '') | length > 0 }}"
  variables:
    txt: "{{ trigger.to_state.state }}"
  action:
    - choose:
        - conditions:
            - condition: template
              value_template: "{{ (trigger.to_state.state or '') | regex_findall('[^ -~]') | count > 0 }}"
          sequence:
            - service: androidtv.adb_command
              target: { entity_id: media_player.android_tv_192_168_1_20 }
              data:
                command: >-
                  ime set com.android.adbkeyboard/.AdbIME; sleep 1;
                  am broadcast -a ADB_INPUT_B64 --es msg '{{ txt | base64_encode }}'; sleep 1;
                  ime set com.sohu.inputmethod.sogou.tv/.SogouIME
      default:
        - service: androidtv.adb_command
          target: { entity_id: media_player.android_tv_192_168_1_20 }
          data:
            command: >-
              input text '{{ txt | replace(' ', '%s') | replace("'", '') }}'
    - delay: "00:00:02"
    - service: input_text.set_value
      target: { entity_id: input_text.t1_shu_ru_wen_zi }
      data: { value: "" }
```

> **必须用 `mode: queued`**：如果用 `restart`，用户连着发两条时第一条会被打断，
> 而打断发生在「切到 AdbIME」和「切回搜狗」之间 —— 输入法就永远停在 ADBKeyboard 上了。

---

## 五、使用前提（很重要）

中文能打进去，但**落点得先准备好**：

1. 在电视上用遥控器点开搜索框，让光标在里面闪
2. 再在面板上输入文字

如果光标不在输入框里，广播一样会成功（`Broadcast completed: result=0`），
但文字没有落点，看起来就是「什么都没发生」。

面板上的标题也写明了这一点：**发送文字到盒子（支持中文，光标要先在输入框里）**。

---

## 六、实测记录

在同花顺搜索框（`com.hexin.plat.androidTV`，EditText 限长 6 字符）上验证：

| 操作 | 结果 |
|---|---|
| 广播 `ADB_INPUT_TEXT zzz`（框内已有 5 字符） | 只进 `z`——不是失败了，是到长度上限 |
| 清空后广播 `ADB_INPUT_B64`（`贵州茅台`） | `贵州茅台` ✅ |
| 整个流程结束时 | 默认输入法已自动切回搜狗 ✅ |
| `input_text` 实体 | 自动回空 ✅ |

> 如果测试时发现「只进了一个字」，先确认目标输入框有没有 maxLength，别急着怀疑通道。
