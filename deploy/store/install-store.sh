#!/usr/bin/env bash
# 存储面安装(正序):garage 容器 -> garage 初始化(桶/密钥/授权)-> s2-lite 容器 -> basin
# 用法: deploy/store/install-store.sh [env文件]
# 幂等:已有件复用,不重建不破坏;产物密钥落 deploy/.store-credentials(600,gitignore)。
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/../lib.sh"
load_env "${1:-$HERE/../env}"

need ssh; need curl; need openssl
STORE="$STORE_NODE_SSH"
CREDS="$HERE/../.store-credentials"

# ---------- 1. 宿主预检与目录 ----------
log "预检 $STORE(docker)"
ssh "$STORE" 'command -v docker >/dev/null 2>&1' || die "$STORE 缺 docker"
ssh "$STORE" "mkdir -p /opt/garage/data /opt/garage/meta"

# ---------- 2. garage 配置(已存在不动)与容器 ----------
if ! ssh "$STORE" "[ -f /opt/garage/garage.toml ]"; then
  log "写 /opt/garage/garage.toml"
  ssh "$STORE" "cat > /opt/garage/garage.toml" <<EOF
metadata_dir = "/var/lib/garage/meta"
data_dir = "/var/lib/garage/data"
db_engine = "lmdb"
replication_factor = 1
rpc_bind_addr = "[::]:${GARAGE_RPC_PORT:-3901}"
rpc_secret = "${GARAGE_RPC_SECRET}"
[s3_api]
s3_region = "garage"
api_bind_addr = "[::]:${GARAGE_S3_PORT:-3900}"
root_domain = ".s3.garage"
[s3_web]
bind_addr = "[::]:3902"
root_domain = ".web.garage"
[admin]
api_bind_addr = "[::]:${GARAGE_ADMIN_PORT:-3903}"
admin_token = "${GARAGE_ADMIN_TOKEN}"
metadata_fsync = true
data_fsync = true
metadata_auto_snapshot_interval = "1h"
EOF
fi

log "garage 容器(host 网络,unless-stopped)"
ssh "$STORE" 'docker inspect garage >/dev/null 2>&1 || docker run -d --name garage \
  --network host --restart unless-stopped \
  -v /opt/garage/garage.toml:/etc/garage.toml:ro \
  -v /opt/garage/data:/var/lib/garage/data \
  -v /opt/garage/meta:/var/lib/garage/meta \
  dxflrs/garage:v1.1.0'
ssh "$STORE" 'docker start garage >/dev/null 2>&1 || true'

STORE_IP=$(ssh "$STORE" "hostname -I | awk '{print \$1}'")
S3_URL="http://${STORE_IP}:${GARAGE_S3_PORT:-3900}"
ADMIN_URL="http://${STORE_IP}:${GARAGE_ADMIN_PORT:-3903}"
S2_URL="http://${STORE_IP}:${S2_PORT:-8090}"
log "等 garage 健康"
wait_http "$ADMIN_URL/health" 60 >/dev/null

# ---------- 3. garage 初始化(桶/密钥/授权)----------
log "garage 初始化"
GARAGE_ADMIN_TOKEN="$GARAGE_ADMIN_TOKEN" \
  bash "$HERE/garage-init.sh" "$ADMIN_URL" "$CREDS" "$S5_BUCKET" "$S2_BUCKET"

# ---------- 4. s2-lite 容器(用后备桶专用 key)----------
. "$CREDS"
log "s2-lite 容器"
if ssh "$STORE" 'docker inspect s2 >/dev/null 2>&1'; then
  ok "s2 容器已在(不动)"
else
  ssh "$STORE" "docker run -d --name s2 --network host --restart unless-stopped \
    -e AWS_ACCESS_KEY_ID='$S2_KEY_ID' \
    -e AWS_SECRET_ACCESS_KEY='$S2_KEY_SECRET' \
    -e AWS_ENDPOINT_URL_S3='http://127.0.0.1:${GARAGE_S3_PORT:-3900}' \
    -e AWS_REGION=garage \
    ghcr.io/s2-streamstore/s2:latest \
    lite --bucket ${S2_BUCKET} --path ${S2_PATH} --port ${S2_PORT:-8090}"
fi
log "等 s2 健康"
wait_http "$S2_URL/health" 60 "OK" >/dev/null

# ---------- 5. basin ----------
log "basin(${BASIN_NAME})"
if curl -fsS "$S2_URL/v1/basins" | grep -q "\"${BASIN_NAME}\""; then
  ok "basin 已在"
else
  curl -fsS -X POST "$S2_URL/v1/basins" -H 'Content-Type: application/json' \
    -d "{\"basin\":\"${BASIN_NAME}\"}" >/dev/null
  ok "basin 建成"
fi

ok "存储面就绪"
echo "S3_URL=$S3_URL"
echo "ADMIN_URL=$ADMIN_URL"
echo "S2_URL=$S2_URL"
echo "BASIN=$BASIN_NAME"
echo "密钥档案: $CREDS(600,已 gitignore)"
