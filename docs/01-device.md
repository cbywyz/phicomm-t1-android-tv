# 01 设备与环境

## 机器参数（实测）

```
型号     斐讯 T1（Phicomm T1）
系统     Android 7.1.2
架构     arm64-v8a
分辨率   1920x1080
输入法   com.sohu.inputmethod.sogou.tv/.SogouIME   （搜狗 TV 输入法）
ADB      ro.adb.secure=0，persist.adb.tcp.port=5555，开机即开
root     有 su（SuperSU），但 SELinux 是 enforcing
```

自带 App（包名，改造时可能用到）：

| 包名 | 是什么 | 备注 |
|---|---|---|
| `app.orchard.tv` | Aerial 桌面 | 第三方桌面，做默认桌面用 |
| `com.hexin.plat.androidTV` | 同花顺 | 启动 Activity `.AndroidLogoActivity` |
| `com.fxrom.launcher.tvlive` | 斐讯直播 | 用 `monkey` 拉起最稳 |
| `com.fxrom.launcher.media` | 斐讯影音 | 同上 |
| `com.dangbeimarket` | 当贝市场 | |
| `com.android.provision` | 开机向导 | **开机停在配对页的元凶，见 docs/05** |

---

## ADB 是怎么开的

T1 出厂就开了网络 ADB，而且 `ro.adb.secure=0`：

```bash
adb shell getprop ro.adb.secure
# 0
adb shell ls /data/misc/adb/adb_keys
# No such file or directory
```

`ro.adb.secure=0` 意味着**没有 RSA 授权机制**——不需要在电视上点「允许调试」，
也不存在 `adb_keys` 白名单。

## 为什么本机 `adb connect` 一直 offline

现象：电脑上 `adb connect 192.168.1.20:5555` 显示 `connected`，但 `adb shell` 立刻 `offline`，
电视上也不会弹授权窗。

原因不是没授权（它压根没有授权机制），而是 `ro.adb.secure=0` 的 adbd 与现代 adb host
的握手流程不匹配。折腾 host 侧参数收益很低。

**结论：不要在本机用 adb，直接走 Home Assistant 的 androidtv 集成。**
集成内部是纯 socket 实现的 adb 协议，不需要 host 授权，能正常下发命令。

调试统一用 [`scripts/adb_helper.py`](../scripts/adb_helper.py)：

```bash
python scripts/adb_helper.py "dumpsys window | grep mCurrentFocus"
```

---

## adbd 是 init 托管的，别手动 stop

`init.rc` 里 adbd 属于 `class core`，**不是 oneshot**。这意味着：

- adbd 崩了会被 init 自动 respawn
- 但你执行 `stop adbd` 时，它会连带杀掉当前 shell（你正跑在 adbd 里）
- 后面那句 `start adbd` 根本没机会执行 → **5555 端口关闭，只能断电重启**

这个坑我踩过，代价是让人跑去拔电源。见 [docs/06](06-pitfalls.md)。

---

## 盒子上的可用工具

```bash
which wget busybox
# /system/xbin/wget
# /system/xbin/busybox
```

有 busybox wget（**不支持 https，也不支持 `-S`**），但足够用来从内网 HTTP 拉文件。
往盒子里传 APK/配置，靠的就是这条链路，见 [docs/04](04-chinese-input.md#安装-adbkeyboard)。
