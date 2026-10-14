#!/usr/bin/env bash
# 节点面安装(linux/mac,在目标节点上执行):
#   tailscale(缺则装) -> herdr 二进制+服务化 -> s5 二进制 -> prim 三命令(uv)
#   -> s5 配置(三端点) -> herdr 互注册
# 用法: install-node.sh <env文件> <credentials文件>
# 前置:本节点与存储宿主/其他节点的 SSH 别名互信已配(见 docs/deploy.md)。
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/../lib.sh"
load_env "${1:?用法: install-node.sh <env> <credentials>}"
CREDS="${2:?用法: install-node.sh <env> <credentials>}"
[ -f "$CREDS" ] || die "缺 $CREDS(存储面 install-store.sh 产出)"

OS=$(uname -s); ARCH=$(uname -m)
[ "$OS" = "Linux" ] || [ "$OS" = "Darwin" ] || die "本脚本面向 linux/mac;win 节点见 docs/deploy.md 手工节"
case "$ARCH" in
  x86_64|amd64) ARCH2=x86_64;;
  aarch64|arm64) ARCH2=aarch64;;
  *) die "未支持架构: $ARCH";;
esac
BIN="$HOME/.local/bin"; mkdir -p "$BIN"
case ":$PATH:" in *":$BIN:"*) ;; *) log "提醒: 把 $BIN 加入 PATH";; esac

# ---------- 1. tailscale ----------
if ! command -v tailscale >/dev/null 2>&1; then
  log "装 tailscale(官方脚本)"
  curl -fsSL https://tailscale.com/install.sh | sh
fi
if ! tailscale status >/dev/null 2>&1; then
  [ -n "${TS_CONTROL_URL:-}" ] || die "TS_CONTROL_URL 未配(纯自托管:headscale 控制面必填)"
  log "tailscale 接入自托管控制面($TS_CONTROL_URL,开 ssh)"
  tailscale up --ssh --login-server="$TS_CONTROL_URL" --hostname="$(hostname -s)"
  die "tailscale 需控制面授权(浏览器或预发 authkey);完成后重跑本脚本"
fi
ok "tailscale 在网"

# ---------- 2. herdr(官方 herdrdev/herdr release,五平台预编译) ----------
if [ ! -x "$BIN/herdr" ]; then
  log "装 herdr 二进制"
  VER="${HERDR_VERSION:-0.9.4}"
  case "$OS-$ARCH2" in
    Linux-x86_64)   ASSET=herdr-linux-x86_64;;
    Linux-aarch64)  ASSET=herdr-linux-aarch64;;
    Darwin-x86_64)  ASSET=herdr-macos-x86_64;;
    Darwin-aarch64) ASSET=herdr-macos-aarch64;;
    *) die "无 herdr 预编译资产($OS-$ARCH2):设 HERDR_BIN_URL 直链";;
  esac
  if [ -n "${HERDR_BIN_URL:-}" ]; then
    curl -fsSL "$HERDR_BIN_URL" -o "$BIN/herdr" && chmod +x "$BIN/herdr"
  else
    curl -fsSL "https://github.com/herdrdev/herdr/releases/download/v${VER}/${ASSET}" \
      -o "$BIN/herdr" && chmod +x "$BIN/herdr"
  fi
fi
"$BIN/herdr" --version >/dev/null 2>&1 || die "herdr 二进制不可执行"
ok "herdr $("$BIN/herdr" --version 2>/dev/null | head -1)"

# herdr server 服务化
if [ "$OS" = "Linux" ]; then
  if ! systemctl is-active --quiet herdr-server 2>/dev/null; then
    log "systemd 服务化 herdr-server"
    sudo tee /etc/systemd/system/herdr-server.service >/dev/null <<EOF
[Unit]
Description=herdr headless server
After=network-online.target

[Service]
User=$USER
ExecStart=$BIN/herdr server
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF
    sudo systemctl daemon-reload && sudo systemctl enable --now herdr-server
  fi
else
  if ! launchctl list 2>/dev/null | grep -q com.herdr.server; then
    log "launchd 服务化 com.herdr.server"
    cat > "$HOME/Library/LaunchAgents/com.herdr.server.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.herdr.server</string>
  <key>ProgramArguments</key>
  <array><string>$BIN/herdr</string><string>server</string></array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>/tmp/herdr-server.log</string>
  <key>StandardErrorPath</key><string>/tmp/herdr-server.err</string>
</dict>
</plist>
EOF
    launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.herdr.server.plist" 2>/dev/null \
      || launchctl load "$HOME/Library/LaunchAgents/com.herdr.server.plist"
  fi
fi
ok "herdr server 服务化"

# ---------- 3. s5 ----------
if [ ! -x "$BIN/s5" ]; then
  log "装 s5(release 资产 + sha256 校验)"
  case "$OS-$ARCH2" in
    Linux-x86_64)   TARGET=x86_64-unknown-linux-gnu;;
    Darwin-x86_64)  TARGET=x86_64-apple-darwin;;
    Darwin-aarch64) TARGET=aarch64-apple-darwin;;
    *) die "无 s5 预编译资产($OS-$ARCH2):cargo 源装 https://github.com/raystyle/s5_rs 后放 $BIN/s5";;
  esac
  ASSET=$(curl -fsSL "https://api.github.com/repos/raystyle/s5_rs/releases/latest" \
    | python3 -c "
import json,sys
for a in json.load(sys.stdin).get('assets',[]):
    if '$TARGET' in a['name'] and a['name'].endswith(('.tar.gz','.zip')):
        print(a['browser_download_url']); break")
  [ -n "$ASSET" ] || die "release 未找到 $TARGET 资产"
  TMP=$(mktemp -d)
  curl -fsSL "$ASSET" -o "$TMP/s5.pkg"
  curl -fsSL "$ASSET.sha256" -o "$TMP/s5.sha256" || true
  if [ -f "$TMP/s5.sha256" ]; then
    (cd "$TMP" && printf '%s  %s\n' "$(cat s5.sha256 | awk '{print $1}')" s5.pkg | shasum -a 256 -c - >/dev/null 2>&1 \
      || { cd "$TMP" && sha256sum -c <(printf '%s  %s\n' "$(cat s5.sha256 | awk '{print $1}')" s5.pkg) >/dev/null 2>&1; }) \
      || die "s5 校验不过"
  fi
  case "$ASSET" in
    *.tar.gz)
      tar -xzf "$TMP/s5.pkg" -C "$TMP"
      find "$TMP" -name s5 -type f -exec mv {} "$BIN/s5" \;
      chmod +x "$BIN/s5"
      ;;
    *.zip)
      need unzip
      unzip -oq "$TMP/s5.pkg" -d "$TMP"
      find "$TMP" -name 's5*' -type f -exec cp {} "$BIN/s5" \;
      chmod +x "$BIN/s5"
      ;;
  esac
  rm -rf "$TMP"
fi
"$BIN/s5" --version >/dev/null 2>&1 || die "s5 二进制不可执行"
ok "s5 $("$BIN/s5" --version 2>/dev/null | head -1)"

# ---------- 4. prim 三命令(uv) ----------
if ! command -v uv >/dev/null 2>&1; then
  log "装 uv"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi
log "装 prim(agents/shares/streams)"
if [ -n "${PRIM_SRC:-}" ]; then
  uv tool install --force "$PRIM_SRC"
else
  uv tool install --force "git+https://github.com/raystyle/herdr-mesh#subdirectory=src"
fi
for c in agents shares streams; do
  command -v "$c" >/dev/null 2>&1 || die "$c 未上 PATH(检查 $BIN 与 shell 重哈希)"
done
ok "prim 三命令在位(agents/shares/streams)"

# ---------- 5. s5 配置(三端点)----------
. "$CREDS"
STORE_ADDR=$(getent hosts "$STORE_NODE_SSH" 2>/dev/null | awk '{print $1}' || true)
[ -n "$STORE_ADDR" ] || STORE_ADDR=$(python3 -c "import socket;print(socket.gethostbyname('$STORE_NODE_SSH'))" 2>/dev/null || true)
[ -n "$STORE_ADDR" ] || die "解析不了 $STORE_NODE_SSH(SSH 别名/tailnet 名先通)"
mkdir -p "$HOME/.config/s5"; umask 077
cat > "$HOME/.config/s5/config.toml" <<EOF
[s3]
admin_token = "${GARAGE_ADMIN_TOKEN}"
endpoint = "http://${STORE_ADDR}:${GARAGE_S3_PORT:-3900}"
region = "garage"
bucket = "${S5_BUCKET}"
access_key_id = "${S3_KEY_ID}"
secret_access_key = "${S3_KEY_SECRET}"

[s2]
endpoint = "http://${STORE_ADDR}:${S2_PORT:-8090}"
basin = "${BASIN_NAME}"
token = "ignored"
EOF
ok "s5 配置落位(~/.config/s5/config.toml,600)"

# ---------- 6. herdr 互注册 ----------
for p in $HERDR_PEERS; do
  if ! "$BIN/herdr" machine list 2>/dev/null | grep -q "$p"; then
    log "注册对端: $p"
    "$BIN/herdr" machine add "$p" || log "machine add $p 未成(手工: herdr machine add $p)"
  fi
done
ok "节点面就绪($OS $ARCH2)"
