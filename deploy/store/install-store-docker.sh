#!/usr/bin/env bash
# 存储面 docker compose 部署(与 install-store.sh 脚本形二选一;compose 形更贴 docker 习惯)
# 用法: deploy/store/install-store-docker.sh [env文件]
# 流程:落配置 -> 首起 garage -> garage-init(桶/钥/授权)-> 回填 S2 钥 -> 全栈 up -> basin
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/../lib.sh"
need docker; need openssl; need curl

load_env "${1:-$HERE/../env}"
CREDS="$HERE/.store-credentials"
STORE_IP=$(hostname -I | awk '{print $1}')
ADMIN_URL="http://${STORE_IP}:${GARAGE_ADMIN_PORT:-3903}"
S2_URL="http://${STORE_IP}:${S2_PORT:-8090}"

# 1) 配置件(存在即跳)
[ -f "$HERE/garage.toml" ] || {
  RPC=$(rand_hex); ADMIN=$(rand_hex)
  sed -e "s|<openssl rand -hex 32>|$RPC|" -e "s|<openssl rand -hex 32>|$ADMIN|" \
    "$HERE/garage.toml.example" > "$HERE/garage.toml"
  umask 077; { echo "GARAGE_RPC_SECRET=$RPC"; echo "GARAGE_ADMIN_TOKEN=$ADMIN"; } > "$HERE/.garage.secrets"
  ok "garage.toml 铸成(密钥档 .garage.secrets,600)"
}

# 2) 首起 garage(单件)
log "首起 garage"
( cd "$HERE" && docker compose --env-file <(cat "$HERE/../env" 2>/dev/null; echo "S2_KEY_ID=x"; echo "S2_KEY_SECRET=x") up -d garage 2>/dev/null ) \
  || docker run -d --name garage --network host --restart unless-stopped \
       -v "$HERE/garage.toml":/etc/garage.toml:ro -v garage-data:/var/lib/garage/data -v garage-meta:/var/lib/garage/meta \
       dxflrs/garage:v1.1.0
log "等 garage 健康"
wait_http "$ADMIN_URL/health" 60 >/dev/null

# 3) 初始化(桶/钥/授权;幂等)
. "$HERE/.garage.secrets"
GARAGE_ADMIN_TOKEN="$GARAGE_ADMIN_TOKEN" \
  bash "$HERE/garage-init.sh" "$ADMIN_URL" "$CREDS" "${S5_BUCKET:-mesh-files}" "${S2_BUCKET:-s2-data}"

# 4) 回填 S2 钥到 store.env -> 全栈起
. "$CREDS"
ENVF="$HERE/store.env"
if [ ! -f "$ENVF" ]; then
  sed -e "s|__gen__|$GARAGE_RPC_SECRET|" "$HERE/store.env.example" > /dev/null 2>&1 || true
  umask 077
  cat > "$ENVF" <<EOF
GARAGE_S3_PORT=${GARAGE_S3_PORT:-3900}
GARAGE_ADMIN_PORT=${GARAGE_ADMIN_PORT:-3903}
S2_PORT=${S2_PORT:-8090}
S2_BUCKET=${S2_BUCKET:-s2-data}
S2_PATH=${S2_PATH:-s2lite}
S2_KEY_ID=$S2_KEY_ID
S2_KEY_SECRET=$S2_KEY_SECRET
EOF
  # garage.toml 里的密钥同步进 env(compose 不用,留档)
  grep -q GARAGE_RPC_SECRET "$ENVF" || echo "GARAGE_RPC_SECRET=$GARAGE_RPC_SECRET" >> "$ENVF"
fi
log "全栈起(garage + s2)"
( cd "$HERE" && docker compose --env-file "$ENVF" up -d )
log "等 s2 健康"
wait_http "$S2_URL/health" 60 "OK" >/dev/null

# 5) basin
BASIN="${BASIN_NAME:-mesh-basin}"
if ! curl -fsS "$S2_URL/v1/basins" | grep -q "\"$BASIN\""; then
  curl -fsS -X POST "$S2_URL/v1/basins" -H 'Content-Type: application/json' \
    -d "{\"basin\":\"$BASIN\"}" >/dev/null
  ok "basin 建成"
else
  ok "basin 已在"
fi

ok "存储栈就绪(compose 形)"
echo "S3=http://${STORE_IP}:3900  ADMIN=$ADMIN_URL  S2=$S2_URL  BASIN=$BASIN"
