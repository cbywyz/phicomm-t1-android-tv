#!/usr/bin/env bash
# 把 ADBKeyboard 装进盒子并启用（不设为默认输入法）。
#
# 用法：
#   export HA_URL=http://192.168.1.10:8123
#   export HA_TOKEN=xxxx
#   ./install_adbkeyboard.sh http://192.168.1.1/adbkb.apk
#
# 第一个参数是 APK 的内网 HTTP 地址。盒子自带 busybox wget，
# 不支持 https，所以必须先把这个 apk 放到内网 80 端口的静态服务上。
# （放 HA 的 8123 端口会报 wget: error getting response，别试）
#
# 下载 APK：
#   curl -LO https://raw.githubusercontent.com/senzhk/ADBKeyBoard/master/ADBKeyboard.apk

set -euo pipefail

APK_URL="${1:-}"
if [ -z "$APK_URL" ]; then
  echo "用法: $0 <内网 APK 地址>  例如 http://192.168.1.1/adbkb.apk" >&2
  exit 1
fi

HERE="$(cd "$(dirname "$0")" && pwd)"
PY="${PYTHON:-python3}"

run_adb() {
  "$PY" "$HERE/adb_helper.py" "$1"
}

echo "==> 检查盒子连通性"
run_adb "getprop ro.build.version.release"

echo "==> 下载 APK"
run_adb "wget -O /data/local/tmp/adbkb.apk $APK_URL; ls -l /data/local/tmp/adbkb.apk"

echo "==> 安装"
run_adb "pm install -r /data/local/tmp/adbkb.apk"

echo "==> 启用输入法（不设为默认！）"
run_adb "ime enable com.android.adbkeyboard/.AdbIME; ime list -s"

echo "==> 当前默认输入法（应该还是搜狗/系统输入法）"
run_adb "settings get secure default_input_method"

cat <<'EOF'

完成。可以这样测一句中文（先用遥控器把光标点进某个搜索框）：

  python3 adb_helper.py "ime set com.android.adbkeyboard/.AdbIME; sleep 1;
    am broadcast -a ADB_INPUT_B64 --es msg '5Lit5paH'; sleep 1;
    ime set com.sohu.inputmethod.sogou.tv/.SogouIME"

  5Lit5paH 是「中文」的 base64。

  ⚠️ 一定要在最后切回原输入法，否则家里人用遥控器就打不出字了。
EOF
