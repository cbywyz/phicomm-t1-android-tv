# 01 设备与环境

这一章把「我到底在什么机器、什么系统、什么环境上做的」讲清楚。
**换一台机器、换一个固件，下面一半的结论就不成立了**，所以先对齐环境再往下看。

---

## 一句话结论

斐讯 T1（Amlogic **S912**，2G/16G），跑的是 **第三方官改的 Android 7.1.2 固件
`T1_ROM_20211231`**，内核还是 2018 年原厂那只；自带 SuperSU 但 SELinux 是 enforcing；
网络 ADB 出厂就开着、且**没有 RSA 授权机制**；我用 **Home Assistant 的 androidtv 集成**
当唯一控制通道。

---

## 1. 硬件规格（全部实测，非查资料）

| 项目 | 值 | 取自 |
|---|---|---|
| 品牌 / 型号 | Phicomm **T1** | `ro.product.manufacturer` / `ro.product.model` |
| 内部代号 | **q201** | `ro.product.device` |
| 主板版本 | `DB1_MB_V1.0` | `ro.phicomm.hardware.version` |
| SoC | **Amlogic S912**，8 核 Cortex-A53 | `ro.board.platform=gxm`、`/proc/cpuinfo` |
| GPU | Mali-T820（S912 标配） | — |
| 内存 | 标称 2 GB，**系统实际可用 1 782 MB** | `/proc/meminfo` MemTotal=1825384 kB |
| 存储 | 16 GB eMMC：`/data` 11 G、`/system` 1.9 G | `df -h` |
| 架构 | arm64-v8a（兼容 armeabi-v7a） | `ro.product.cpu.abilist` |
| 输出分辨率 | **1920×1080 / 240 dpi** | `wm size` / `wm density` |
| 有线网卡 MAC | `68:db:54:xx:xx:xx` | `ip addr show eth0` |
| 无线网卡 MAC | `80:c5:f2:xx:xx:xx`（5 GHz，实测 433 Mbps） | `dumpsys wifi` |
| 蓝牙 | 有，配合原厂蓝牙遥控（`KehwinBLE`） | `/system/app` |

> S912 支持 4K 输出，但我这台**面板按 1080p 跑**（`wm size` 实测 1920×1080）。
> 面板布局的坐标、按键尺寸都是按这个分辨率调的。

---

## 2. 固件身份：到底是哪个系统

### 2.1 版本号

```
ro.build.display.id       T1_ROM_20211231
ro.phicomm.inner.version  T1_ROM_20211231
ro.phicomm.outer.version  T1_ROM_20211231
ro.build.fingerprint      Phicomm/q201/q201:7.1.2/NHG47L/20211231:user/dev-keys
ro.bootimage.build.fingerprint
                          Phicomm/q201/q201:7.1.2/NHG47L/20180123:user/dev-keys
ro.build.version.release  7.1.2      （SDK 25）
ro.build.date             Fri Dec 31 14:47:19 CST 2021
```

**这是一种「官改包」**，不是官方原厂 OTA，也不是从源码重编译的 AOSP。判断依据有三条：

1. `ro.build.display.id` 被改成了 `T1_ROM_20211231`（2021-12-31 打包），
   而 `ro.bootimage.build.fingerprint` 里还是 **`20180123`** ——
   **系统分区是 2021 年改的，boot 分区还是 2018 年原厂那只**。
2. 内核是原厂的：

   ```
   Linux version 3.14.29 (jenkins@slave2)
   gcc 4.9.3 (Ubuntu/Linaro 4.9.3-13ubuntu2)
   #1 SMP PREEMPT Tue Jan 23 14:50:03 CST 2018
   ```

   `jenkins@slave2` + 2018-01-23，是斐讯原厂编译机的特征，官改包不会重编内核。
3. `ro.build.tags=dev-keys`、`ro.build.type=user`、`ro.otaupdateurl=` 空 ——
   斐讯官方 OTA 通道已被摘掉，刷完就断更。

### 2.2 这个固件「改」了什么

从现场残留能看出来的是：

| 改动 | 证据 |
|---|---|
| 预装了一堆第三方 TV 应用（当贝、SmartTube、腾讯视频等） | `pm list packages -3` 见第 5 节 |
| 保留了原厂桌面 `TvdLauncher`、直播 `Tvd_Tvlive`、影音 `Tvd_Media` | `/system/app` |
| 集成 SuperSU 2.82 做 root | `/system/xbin/su`，`su --version → 2.82:SUPERSU` |
| 保留蓝牙遥控服务 `KehwinBLE`（原厂遥控还能用） | `/system/app/KehwinBLE` |
| 开机向导 `com.android.provision` 没删（这是个坑） | 见 docs/05 |

> ⚠️ 我不知道也不打算猜这个包是哪位作者出的（恩山/ ZNDS 上叫 `T1_ROM_2021xxxx` 的包有好几个版本）。
> **重要的一条：`T1_ROM_20211231` 只是一个 display id，不同作者的包可能都叫这个名字。**
> 所以下面给了一条「一条命令核对」的办法，请以实际输出为准。

### 2.3 一条命令核对你的机器是不是同一套环境

```bash
python scripts/probe_device.py
```

它会把你机器的硬件、固件、root、分区、网络、预装应用一次性打出来。
**贴 issue 时直接贴这段输出**，比描述「我的是 T1」有用得多。

关键几行对不上（比如 `ro.build.version.release` 是 9、`ro.board.platform` 不是 `gxm`、
`su` 不在 `/system/xbin/`），说明你的固件跟本文不同，第 4、5、6 节的结论要重新验证。

### 2.4 出厂系统与刷机退路

- **出厂固件已经查不到了**：`ro.otaupdateurl` 为空，斐讯的 OTA 服务器早停了，
  系统分区也已被这个官改包覆盖，没法从机器里反推出出厂版本。
- **想换系统只有一条路：USB 线刷**（Amlogic USB Burning Tool + 双公头 USB 线 + 短接点）。
  因为没有自定义 recovery，**不存在「卡刷回去」这种退路**。
- 社区里有 T1 的其它选择（**仅供参考，本项目未验证**）：
  - 官方/官改 Android 7.1.2 线刷包（回到出厂状态）
  - Armbian / FnNAS 之类的 Linux 发行版（S912 的 `amlogic-s9xxx` 系列镜像）
  - 刷了 Linux 之后 **Android TV 集成就废了**，本仓库的遥控面板也不再适用

> 结论：**本文所有改动都不需要刷机**，也建议不刷。
> 你要的是「能用 HA 遥控」，现在的固件已经满足；刷机只会把唯一的退路也花掉。

---

## 3. 系统与安全状态

```
ro.build.type        user
ro.build.tags        dev-keys
ro.debuggable        0            ← 不是 eng/userdebug 包
ro.secure            1
ro.adb.secure        0            ← 关键：ADB 无授权
getenforce           Enforcing    ← SELinux 开着
ro.romhelper.root    0
```

### 3.1 root 是「有，但残缺」

```
$ which su
/system/xbin/su                    (104384 字节，2018-04-16)
$ su --version
2.82:SUPERSU
$ su -c id
uid=0(root) gid=0(root) groups=0(root) context=u:r:toolbox:s0
```

`uid=0` 说明能提权，但 **context 停在 `u:r:toolbox:s0`，不是 `u:r:su:s0`**。
这是 SuperSU 2.82 在这个内核上没拿到完整 domain 的典型表现，后果很实际：

- ✅ 能 `mount -o rw,remount /system`、能改 `/system` 下的文件、能 `pm disable-user`
- ❌ **`/system/su.d/` 下的脚本不会被扫描执行**（没有 su.d 服务在跑）
- ❌ **`/system/bin/install-recovery.sh` 开机会被 SELinux 拒绝**
  （`does not have a SELinux domain defined`）
- ❌ 改 init 的 service 也一样起不来

所以**别指望在盒子上装开机自启脚本**。我试过两条路（su.d、install-recovery 槽位），
全部失败并已清理干净（`/system` 已 remount 回只读）。替代方案是 HA 侧的离线自愈，见 docs/02。

### 3.2 没有自定义 Recovery

```
$ ls /system/recovery*        → No such file or directory
$ ls /dev/block/by-name       → 空（SELinux 挡住）
```

**没有 TWRP / 没有第三方 recovery**，`/system/bin/install-recovery.sh` 也不存在。
也就是说：**刷坏了只能走 USB 线刷（Amlogic USB Burning Tool + 短接），没有卡刷退路。**
动手改 `/system` 之前，务必确认你手边有双公头 USB 线和短接点资料。

---

## 4. 分区与存储

```
Filesystem            Size  Used Avail Use%  Mounted on
/dev/block/data        11G  2.7G  8.4G  25%  /data
/dev/block/system     1.9G  840M  1.1G  43%  /system
```

- `/system` 只剩 1.1 G 可写 —— 装大应用、拷 APK 进系统分区要算好空间
- `/data` 剩 8.4 G，日常够用
- `swap` 只有 31 MB（基本等于没有），内存吃紧时没有缓冲
- `/cache` 是 ext4，正常挂载

---

## 5. 应用清单（改造时会用到的）

### 5.1 系统预装（`/system/app`）

| 目录名 | 是什么 | 动它的后果 |
|---|---|---|
| `TvdLauncher` | 斐讯原厂桌面 | 换桌面后可留着不启动，**不建议直接停**（有些系统弹窗依赖它） |
| `Tvd_Tvlive` | 斐讯直播 | 停掉后「直播」入口失效 |
| `Tvd_Media` | 斐讯影音 | 同上 |
| `Tvd_Diyone` / `Tvdxiaobaifile` / `Tvdhpplay` | 斐讯自带小工具 / 文件管理 / 投屏 | 可停 |
| `KehwinBLE` | **蓝牙遥控服务** | **停掉原厂遥控器就废了，绝对别动** |
| `Superuser` | SuperSU 管理端 | 停掉后授权弹窗不出来 |
| `sogou` | 搜狗 TV 输入法 | **默认输入法，停掉遥控器九宫格输入就废了** |
| `shafamarket` | 沙发市场 | 可停（我已停用） |
| `webview` | 系统 WebView（老版本） | 部分 App 依赖，别动 |
| `Bluetooth` / `BluetoothRemote` / `CertInstaller` / `KeyChain` / `HTMLViewer` / `ExtShared` / `Dig` / `UserDictionaryProvider` | Android 标准组件 | 别动 |

### 5.2 第三方应用（`pm list packages -3`，我机器的现状）

| 包名 | 是什么 | 备注 |
|---|---|---|
| `app.orchard.tv` | **Aerial 桌面** | 已设为默认 Home，见 docs/05 |
| `com.hexin.plat.androidTV` | **同花顺** | 启动 Activity `.AndroidLogoActivity` |
| `com.dangbei.tvlauncher` | 当贝桌面 | 备用桌面，未启用 |
| `com.dangbeimarket` | 当贝市场 | |
| `com.liskovsoft.smarttubetv.beta` | SmartTube（去广告 YouTube） | 有可编辑的搜索框，**测中文输入就用它** |
| `com.ktcp.video` | 腾讯视频 TV 版 | |
| `com.xiaodianshi.tv.yst` | 云视听小电视（B 站 TV） | |
| `com.ixigua.android.tv.wasu` | 西瓜视频 TV | |
| `com.estrongs.android.pop` | ES 文件浏览器 | |
| `com.android.adbkeyboard` | **ADBKeyboard**（本项目装的） | 中文输入用，见 docs/04 |
| `com.ystv` / `com.trim.tv` / `com.gitvdemo.video` | 未逐一确认 | `pm dump <包名>` 自己看 |

### 5.3 我停用的包

```
com.android.provision    ← 开机向导，开机停在配对页的元凶，见 docs/05
com.shafa.market         ← 沙发市场
```

查看/恢复：

```bash
pm list packages -d                      # 看已停用
pm enable com.android.provision          # 恢复
```

---

## 6. 网络环境

| 项目 | 值 |
|---|---|
| 盒子 IP | 由路由器 DHCP 分配（我这台是 `192.168.1.137`，**别写死，会变**） |
| 无线 | 连 5 GHz，实测 433 Mbps |
| 有线 | eth0 存在，本机未接 |
| ADB 端口 | `5555`，`persist.adb.tcp.port=5555`，**开机即开** |
| HA | 同一网段，`http://<HA_IP>:8123` |

> 实体名里的 IP 是 HA 自动生成的（`media_player.android_tv_192_168_1_137`）。
> **盒子换 IP，实体名就变了**，遥控面板里的所有引用都要跟着改。
> 建议在路由器上给盒子做 DHCP 静态绑定。

---

## 7. Home Assistant 侧环境

| 项目 | 值 |
|---|---|
| HA 版本（验证时） | **2026.9.3** |
| 集成 | `androidtv`（通过 ADB 连接 5555） |
| 实体 | `media_player.android_tv_<ip>`、`remote.android_tv_<ip>` |
| 面板依赖 | HACS：`mushroom`、`bubble-card`、`universal-remote-card` |
| 辅助实体 | `input_text.t1_shu_ru_wen_zi`、`input_boolean.t1_shu_zi_jian_pan` |

HA 版本低于 2023.x 时，`config/entity_registry/list` 的字段和 `render_template` 的行为可能有差异，
面板 YAML 是纯前端配置，不受影响，但脚本里的 WebSocket 命令要对一下版本。

---

## 8. 盒子上能用的命令行工具

```bash
$ which wget busybox
/system/xbin/wget
/system/xbin/busybox
```

- 有 `busybox`，常用命令基本齐
- `wget` **不支持 https，也不支持 `-S`** —— 只能从内网 HTTP 拉文件
- **没有 `curl`**
- 有 `toybox` 的部分命令
- `input`（keyevent / text / tap / swipe）可用 —— 遥控面板的按键全靠它

往盒子里传文件就靠这条链路：电脑 → 主路由 HTTP 根目录 → 盒子 `wget`，
见 [docs/04](04-chinese-input.md#安装-adbkeyboard)。

---

## 9. 性能现状（决定你能装多少东西）

```
MemTotal     1782 MB
MemFree      ~60 MB      ← 空闲内存很少（随负载浮动，几十 MB 量级）
MemAvailable ~850 MB
Swap           31 MB      ← 基本为零
load average   3.8 / 3.9 / 3.8   ← 8 核，长期 3~4，不算轻松
```

- 2 G 内存 + Android TV + 一个 1080p 桌面，开机后可用内存只剩 800 多 MB
- **别在盒子上装 NAS/下载/服务端类应用**，会卡到遥控都延迟
- 想省内存：停掉不用的第三方 App（`pm disable-user`），换轻量桌面（Aerial 就是这个思路）

---

## 10. ADB 是怎么开的

T1 出厂就开了网络 ADB，而且 `ro.adb.secure=0`：

```bash
adb shell getprop ro.adb.secure
# 0
adb shell ls /data/misc/adb/adb_keys
# No such file or directory
```

`ro.adb.secure=0` 意味着**没有 RSA 授权机制**——不需要在电视上点「允许调试」，
也不存在 `adb_keys` 白名单。

## 11. 为什么本机 `adb connect` 一直 offline

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

## 12. adbd 是 init 托管的，别手动 stop

`init.rc` 里 adbd 属于 `class core`，**不是 oneshot**。这意味着：

- adbd 崩了会被 init 自动 respawn
- 但你执行 `stop adbd` 时，它会连带杀掉当前 shell（你正跑在 adbd 里）
- 后面那句 `start adbd` 根本没机会执行 → **5555 端口关闭，只能断电重启**

这个坑我踩过，代价是让人跑去拔电源。见 [docs/06](06-pitfalls.md)。
