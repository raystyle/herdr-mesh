#!/usr/bin/env bash
# 本机最小验证:单机全链(存储两容器 + 节点件 + 七命令)装好并冒烟
# 用法: smoke/local.sh
# 前置:本机 linux/mac,已装 docker 与 curl/openssl/ssh;能 sudo(仅装服务用)。
#      全程只动本机:数据目录 ./local-data,不碰 /opt,不碰远端。
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/../deploy/lib.sh"
need docker; need curl; need openssl; need ssh

# ---- 参数(可环境变量覆盖)----
S3_PORT="${LOCAL_S3_PORT:-13900}"
RPC_PORT="${LOCAL_RPC_PORT:-13901}"
WEB_PORT="${LOCAL_WEB_PORT:-13902}"
ADMIN_PORT="${LOCAL_ADMIN_PORT:-13903}"
S2_PORT="${LOCAL_S2_PORT:-18090}"
BASIN="mesh-local-basin"
FBUCKET="mesh-files-local"
S2BUCKET="s2-data-local"
ROOT="$HERE/.local-mesh"
CREDS="$ROOT/.store-credentials"
NAMES="garage-mesh-local s2-mesh-local"

cleanup() {
  for n in $NAMES; do docker rm -f "$n" >/dev/null 2>&1 || true; done
  log "已停清容器 $NAMES(数据目录 $ROOT 保留;要全删: rm -rf $ROOT)"
}
trap 'fail "中断;清场"; cleanup; exit 1' INT TERM
[ "${1:-}" = "--clean" ] && { cleanup; exit 0; }

mkdir -p "$ROOT/garage-data" "$ROOT/garage-meta"
RPC_SECRET=$(rand_hex)
ADMIN_TOKEN=$(rand_hex)

# ---------- 一、garage ----------
log "一、garage 容器(端口 ${S3_PORT}/${ADMIN_PORT})"
docker inspect garage-mesh-local >/dev/null 2>&1 \
  || docker run -d --name garage-mesh-local --network host --restart no \
       -v "$ROOT/garage.toml:/etc/garage.toml" \
       -v "$ROOT/garage-data:/var/lib/garage/data" \
       -v "$ROOT/garage-meta:/var/lib/garage/meta" \
       dxflrs/garage:v1.1.0 >/dev/null
[ -f "$ROOT/garage.toml" ] || cat > "$ROOT/garage.toml" <<EOF
metadata_dir = "/var/lib/garage/meta"
data_dir = "/var/lib/garage/data"
db_engine = "lmdb"
replication_factor = 1
rpc_bind_addr = "[::]:${RPC_PORT}"
rpc_secret = "${RPC_SECRET}"
[s3_api]
s3_region = "garage"
api_bind_addr = "[::]:${S3_PORT}"
root_domain = ".s3.garage"
[s3_web]
bind_addr = "[::]:${WEB_PORT}"
root_domain = ".web.garage"
[admin]
api_bind_addr = "[::]:${ADMIN_PORT}"
admin_token = "${ADMIN_TOKEN}"
metadata_fsync = true
data_fsync = true
metadata_auto_snapshot_interval = "1h"
EOF
docker start garage-mesh-local >/dev/null 2>&1 || true
S3_URL="http://127.0.0.1:${S3_PORT}"; ADMIN_URL="http://127.0.0.1:${ADMIN_PORT}"
log "等 garage 健康"
wait_http "$ADMIN_URL/health" 60 >/dev/null

# ---------- 二、桶/钥/basin ----------
log "二、初始化(桶/钥/basin)"
GARAGE_ADMIN_TOKEN="$ADMIN_TOKEN" \
  bash "$HERE/../deploy/store/garage-init.sh" "$ADMIN_URL" "$CREDS" "$FBUCKET" "$S2BUCKET"
. "$CREDS"

# ---------- 三、s2-lite ----------
log "三、s2-lite 容器(端口 ${S2_PORT})"
docker inspect s2-mesh-local >/dev/null 2>&1 \
  || docker run -d --name s2-mesh-local --network host --restart no \
       -e AWS_ACCESS_KEY_ID="$S2_KEY_ID" \
       -e AWS_SECRET_ACCESS_KEY="$S2_KEY_SECRET" \
       -e AWS_ENDPOINT_URL_S3="http://127.0.0.1:${S3_PORT}" \
       -e AWS_REGION=garage \
       ghcr.io/s2-streamstore/s2:latest \
       lite --bucket "$S2BUCKET" --path s2lite --port "$S2_PORT" >/dev/null
docker start s2-mesh-local >/dev/null 2>&1 || true
S2_URL="http://127.0.0.1:${S2_PORT}"
log "等 s2 健康"
wait_http "$S2_URL/health" 60 "OK" >/dev/null
if ! curl -fsS "$S2_URL/v1/basins" | grep -q "\"$BASIN\""; then
  curl -fsS -X POST "$S2_URL/v1/basins" -H 'Content-Type: application/json' \
    -d "{\"basin\":\"$BASIN\"}" >/dev/null
fi
ok "basin 在($BASIN)"

# ---------- 四、节点件 ----------
log "四、节点件(herdr/s5/prim)"
[ -x "$HOME/.local/bin/herdr" ] || die "本机无 herdr;先照 docs/deploy.md 第五节装"
herdr --version >/dev/null 2>&1 || die "herdr 不可执行"
if [ ! -x "$HOME/.local/bin/s5" ]; then
  log "装 s5(release 资产)"
  OS=$(uname -s); ARCH=$(uname -m)
  case "$OS-$ARCH" in
    Linux-x86_64)   TARGET=x86_64-unknown-linux-gnu;;
    Darwin-x86_64)  TARGET=x86_64-apple-darwin;;
    Darwin-arm64)   TARGET=aarch64-apple-darwin;;
    *) die "无 s5 预编译($OS-$ARCH):照 docs/deploy.md 装后重跑";;
  esac
  ASSET=$(curl -fsSL "https://api.github.com/repos/raystyle/s5_rs/releases/latest" \
    | python3 -c "
import json,sys
for a in json.load(sys.stdin).get('assets',[]):
    if '$TARGET' in a['name'] and a['name'].endswith(('.tar.gz','.zip')):
        print(a['browser_download_url']); break")
  TMP=$(mktemp -d)
  curl -fsSL "$ASSET" -o "$TMP/s5.pkg"
  case "$ASSET" in
    *.tar.gz)
      tar -xzf "$TMP/s5.pkg" -C "$TMP"
      find "$TMP" -name s5 -type f -exec mv {} "$HOME/.local/bin/s5" \;
      ;;
    *.zip)
      unzip -oq "$TMP/s5.pkg" -d "$TMP"
      find "$TMP" -name 's5*' -type f -exec cp {} "$HOME/.local/bin/s5" \;
      ;;
  esac
  chmod +x "$HOME/.local/bin/s5"; rm -rf "$TMP"
fi
s5 --version >/dev/null 2>&1 || die "s5 不可执行"
command -v uv >/dev/null 2>&1 || { log "装 uv"; curl -LsSf https://astral.sh/uv/install.sh | sh; export PATH="$HOME/.local/bin:$PATH"; }
log "装 prim(七命令)"
uv tool install --force "${PRIM_SRC:-$HERE/../src}" >/dev/null 2>&1
command -v agents >/dev/null 2>&1 || export PATH="$HOME/.local/bin:$PATH"
for c in agents shares streams tasks pipes ports ctxs; do command -v "$c" >/dev/null 2>&1 || die "$c 未上 PATH"; done

# 本机最小 s5 配置(不动 ~/.config/s5;环境变量道,S5_CONFIG 指临时档)
cat > "$ROOT/s5-config.toml" <<EOF
[s3]
admin_token = "${ADMIN_TOKEN}"
endpoint = "${S3_URL}"
region = "garage"
bucket = "${FBUCKET}"
access_key_id = "${S3_KEY_ID}"
secret_access_key = "${S3_KEY_SECRET}"
[s2]
endpoint = "${S2_URL}"
basin = "${BASIN}"
token = "ignored"
EOF
export S5_CONFIG="$ROOT/s5-config.toml"

# ---------- 五、冒烟 ----------
PASS=0; FAIL=0
check() { local n="$1"; shift; log "验: $n"; if "$@" >/dev/null 2>&1; then ok "$n"; PASS=$((PASS+1)); else fail "$n"; FAIL=$((FAIL+1)); fi; }

log "五、冒烟(本机全链)"
check "garage 健康"          curl -fsS "$ADMIN_URL/health"
check "s2 健康"               bash -c "curl -fsS '$S2_URL/health' | grep -q OK"
check "basin 在"              bash -c "curl -fsS '$S2_URL/v1/basins' | grep -q '\"$BASIN\"'"
check "s5 put/get 往返"       bash -c "echo hello | s5 put - local-probe && s5 get local-probe | grep -qx hello"
check "s5 流 append/tail"     bash -c "echo local-probe | s5 append local/probe && s5 tail local/probe -n 5 | grep -q local-probe"
check "agents 手册面"         agents --llms
check "streams 全局面"        streams view
check "tasks 全局面"         tasks view
check "pipes 手册面"         pipes --llms
check "ports 手册面"         ports --llms
check "shares 全局面"         shares view

log "== 结果: $PASS 过 / $FAIL 败 =="
if [ "$FAIL" -eq 0 ]; then
  ok "本机最小验证全绿"
  log "清场: $0 --clean(容器停删;rm -rf $ROOT 连数据全清)"
else
  fail "有败项"; cleanup; exit 1
fi
