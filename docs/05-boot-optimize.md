# 05 开机优化

## 问题一：蓝牙遥控开机后要等一分多钟才能用

### 现象

盒子已经亮屏、桌面都出来了，但遥控器按下去完全没反应，要等 **78–90 秒**才「活过来」。

### 排查过程

```bash
# 1. 看遥控器到底连上没有
adb shell dumpsys bluetooth_manager | grep -i -A3 "BONDED\|connected"

# 2. 盯着蓝牙日志看连接过程
adb shell logcat -c
adb shell logcat -s BluetoothAdapter:V BluetoothDevice:V bt_btif:V
```

日志里能看到这样一轮循环：

```
Connecting to classic HID ...
connect timeout (20s)
Retrying as BLE ...
```

### 原因

这颗蓝牙遥控器同时支持**经典 HID** 和 **BLE HID** 两种模式。开机时系统先按经典 HID 去连，
连不上要等 **20 秒超时**，再换 BLE 重试；这个流程反复几轮，累计就是 1 分半。

**这不是故障，是系统蓝牙栈的连接策略问题**，改不了（需要改系统蓝牙配置，代价大于收益）。

### 能做的一点缓解

如果盒子有「蓝牙遥控器」配对项，在设置里删掉后**只按 BLE 方式重新配对**，
有时能省掉第一轮经典 HID 的重试。不是所有固件都有这个选项，T1 上收益不明显。

> 结论：这个等待只能接受。真正影响体验的是下面这个 —— 开机停在配对页。

---

## 问题二：开机停在配对页，按遥控器没反应

### 现象

开机后屏幕停在「请按遥控器配对」之类的界面（`com.android.provision`），
桌面明明已经在后台起来了，但用户看到的是配对页，以为死机。

### 原因

`com.android.provision`（开机向导）在 package manager 里被注册成了 **HOME 候选**，
和真正的桌面（`app.orchard.tv`）一起参与 HOME 解析，开机时抢到了前台。

### 解决

```bash
adb shell pm disable-user --user 0 com.android.provision
```

禁掉之后 HOME intent 只有一个候选，开机直接进桌面。**实测重启稳定**。

恢复（万一需要）：

```bash
adb shell pm enable com.android.provision
```

---

## 问题三：自带桌面太乱

换成 **Aerial**（`app.orchard.tv`，一个极简的风景时钟桌面），设为默认 Home：

```bash
# 确认它注册了 HOME
adb shell dumpsys package app.orchard.tv | grep -B2 -A6 "android.intent.category.HOME"

# 直接拉起
adb shell am start -n app.orchard.tv/.MainActivity
```

禁掉 `com.android.provision` 之后，`HOME` 键会直接回到 Aerial，不用额外设置默认桌面。

---

## 顺带：把不用的系统包停掉

T1 上可以安全停用的（逐个试，停完立即验证桌面和遥控器正常）：

```bash
adb shell pm disable-user --user 0 <包名>
# 恢复
adb shell pm enable <包名>
# 看已停用的
adb shell pm list packages -d
```

> ⚠️ 不要一次停一堆再验证。**每停 2–3 个就重启一次**，确认桌面能进、遥控器能用。
> 停错了导致进不去桌面，只能靠 adb 救（见 [docs/07](07-recovery.md)）。

---

## 一条经验

判断一个优化有没有用，**不要靠"看起来快了"**，拿数据：

```bash
# 开机到 adb 可用的时间
adb shell getprop sys.boot_completed     # 变成 1 的时刻

# 或者直接看 uptime
adb shell cat /proc/uptime
```

改之前记一次，改之后记一次，差多少一目了然。
