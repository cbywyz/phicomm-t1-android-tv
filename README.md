# 斐讯 T1 盒子接入 Home Assistant：遥控、中文输入、开机优化

一套在**斐讯 T1（Android 7.1.2）**上跑通的完整方案，从零把你的电视盒子接进 Home Assistant，
做成一个能用的遥控面板，并且**能往盒子里打中文**。

所有步骤都在真机上验证过，含踩坑记录。别的 Android TV / 机顶盒（小米盒子、N1、运营商盒子）
思路通用，包名和键码按自己机器改。

---

## 能实现什么

| 能力 | 说明 |
|---|---|
| 完整遥控 | 电源 / 音量 / 静音 / 方向键 / 确定 / 返回 / 主页 / 菜单 / 设置 / 播放控制 |
| 一键启动 App | Aerial 桌面、同花顺、直播、影音、系统设置（换成你自己的包名即可） |
| 数字键盘 | 折叠在弹窗里，用时点开，含**删除 / 清空 / 确定 / 空格 / 小数点** |
| 中文输入 | 面板输一句话 → 自动打进盒子当前的搜索框（临时切输入法，发完自动切回） |
| 开机优化 | 解决蓝牙遥控开机后 1 分多钟才能用、开机停在配对页的问题 |
| 离线自愈 | 盒子重启后 HA 集成卡在 unavailable，掉线满 10 分钟自动重载 |

---

## 相关仓库（同一系列教程）

一个思路：**先把设备接进 Home Assistant，再在 HA 里做各种控制/管控逻辑。**
本仓库负责「盒子怎么接进来 + 遥控 + 中文输入」，下面这些负责接进来之后的事：

- [**ha-tv-kids-lock**](https://github.com/cbywyz/ha-tv-kids-lock) —— 电视家长管控：音量上限锁 / 信号源锁 / 儿童定时锁 / 每日配额。
  **和本仓库共用同一套 HA 底座**：这里把盒子接进来，那边负责接进来之后怎么管孩子看多久。
- [**hisense-vidaa-tv-optimize**](https://github.com/cbywyz/hisense-vidaa-tv-optimize) —— 海信 VIDAA 电视优化实录（换桌面 / 去广告 / 提速 / 信号源）。ADB `pm disable-user` 的思路与本仓库同源。
- [**ha-midea-hualing-ac**](https://github.com/cbywyz/ha-midea-hualing-ac) —— 美的/华凌空调接入 Home Assistant（云端集成教程 + 折腾实录）
- [**ha-hualing-fan-broadlink**](https://github.com/cbywyz/ha-hualing-fan-broadlink) —— 华凌风扇红外遥控接入 HA（Broadlink + 8 键编码库）
- [**gree-yapqf-broadlink-smartir**](https://github.com/cbywyz/gree-yapqf-broadlink-smartir) —— 格力空调 Broadlink + SmartIR 接入 HA
- [**phicomm-aircat-m1**](https://github.com/cbywyz/phicomm-aircat-m1) —— 斐讯悟空 M1 空气检测仪本地复活（自建集成）
- [**ha-auto-gate**](https://github.com/cbywyz/ha-auto-gate) —— 回家 WiFi 自动感知开门（检测器跑在主路由）

---

## 目录

| 文档 | 内容 |
|---|---|
| [01-设备与环境](docs/01-device.md) | 机器参数、ADB 是怎么开的、为什么本机 adb 连不上 |
| [02-接入-HA](docs/02-ha-integration.md) | androidtv 集成、实体、中文命名、活动页显示 |
| [03-遥控面板](docs/03-remote-panel.md) | Universal Remote Card 配置、键码表、DPAD 的坑 |
| [04-数字键盘与中文输入](docs/04-chinese-input.md) | 折叠键盘、ADBKeyboard、base64 广播、临时切 IME |
| [05-开机优化](docs/05-boot-optimize.md) | 遥控器为什么开机慢、配对页、桌面替换、停用清单 |
| [06-踩坑清单](docs/06-pitfalls.md) | 每一条都是踩过的，含错误现场 |
| [07-自救手册](docs/07-recovery.md) | 把自己关在门外了怎么救回来 |

脚本在 [`scripts/`](scripts/)：

| 文件 | 作用 |
|---|---|
| `ha_ws.py` | 极简 HA WebSocket 客户端（只用标准库，读环境变量） |
| `adb_helper.py` | 走 HA 通道下发 adb 命令（带 nonce 校验，解决回显错位） |
| `build_remote_view.py` | 生成遥控面板 Lovelace 视图 JSON |
| `send_text_automation.yaml` | 中文/英文混合输入自动化，可直接粘进 automations.yaml |
| `install_adbkeyboard.sh` | 把 ADBKeyboard 装进盒子（从内网 HTTP 中转） |

---

## 5 分钟上手

```bash
# 1. 环境变量
export HA_URL="http://192.168.1.10:8123"
export HA_TOKEN="你的长期访问令牌"          # HA 左下角头像 → 长期访问令牌

# 2. 确认盒子 ADB 通（在 HA 里已配置 androidtv 集成的前提下）
python scripts/adb_helper.py "getprop ro.build.version.release"
# 期望输出：7.1.2

# 3. 生成遥控面板 JSON（先看，不写入）
python scripts/build_remote_view.py

# 4. 装中文输入法（详见 docs/04）
bash scripts/install_adbkeyboard.sh
```

遥控面板需要三张自定义卡，先在 HACS 里装好：

- `mushroom`（卡片）
- `bubble-card`（弹窗）
- `universal-remote-card`（遥控器本体）

---

## 前提

- Home Assistant 已能访问盒子所在局域网
- 盒子和 HA 在同一网段，`adb connect` 可达 5555
- 盒子已开启 ADB 调试（T1 默认开，见 docs/01）

## 说明

- 文中的 IP、实体 ID、包名都是**示例**，替换成你自己的
- 涉及改 `/system`、停用系统包的操作都有风险，先看对应文档里的「后果」再动手
- 不包含任何个人环境信息（域名、密码、令牌）

## License

MIT
