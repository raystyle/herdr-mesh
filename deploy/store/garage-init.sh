#!/usr/bin/env bash
# garage 初始化:layout 引导 + 两桶(文件桶 + 流后备桶)两钥(客户端钥 + 流服务钥)+ 读写授权
# 用法: GARAGE_ADMIN_TOKEN=... garage-init.sh <admin_url> <credentials_file> <files_bucket> <s2_bucket>
# 事实契约(admin API v1.1.0):POST /v1/layout(数组体)+ /v1/layout/apply;
#   POST /v1/bucket(globalAlias);POST /v1/key(name);POST /v1/bucket/allow
# 幂等:桶与钥已存在则复用;钥密文仅创建时可得,已有钥必须凭 credentials_file 复用。
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/../lib.sh"
need curl; need sed

ADMIN_URL="${1:?用法: garage-init.sh <admin_url> <credentials_file> <files_bucket> <s2_bucket>}"
CREDS="${2:?credentials_file}"
FBUCKET="${3:?files_bucket}"
S2BUCKET="${4:?s2_bucket}"
AUTH="Authorization: Bearer ${GARAGE_ADMIN_TOKEN}"

api() { curl -fsS -H "$AUTH" -H 'Content-Type: application/json' "$@"; }

# ---------- layout 引导(全新库无角色,建桶会 503;幂等:已有角色跳过) ----------
ST=$(api "$ADMIN_URL/v1/status")
NID=$(printf '%s' "$ST" | sed -n 's/.*"node": *"\([0-9a-f]\{64\}\)".*/\1/p')
if ! printf '%s' "$ST" | grep -qE '"role": *\{'; then
  CAP="${GARAGE_CAPACITY_BYTES:-1000000000000}"
  log "layout 引导(单节点 zone1,容量 $CAP 字节)"
  api -X POST "$ADMIN_URL/v1/layout" \
    -d "[{\"id\":\"$NID\",\"zone\":\"zone1\",\"capacity\":$CAP,\"tags\":[]}]" >/dev/null
  api -X POST "$ADMIN_URL/v1/layout/apply" -d '{"version":1}' >/dev/null
  sleep 3
  ok "layout 已布(version 1)"
fi

# ---------- 桶 ----------
# ensure_bucket <名>:打印 bucketId(已存在则复用)
ensure_bucket() {
  local name="$1" id
  id=$(curl -sS -H "$AUTH" "$ADMIN_URL/v1/bucket?globalAlias=$name" \
       | sed -n 's/.*"id": *"\([0-9a-f]*\)".*/\1/p' | head -1 || true)
  if [ -n "$id" ]; then
    ok "桶已在: $name"
    printf '%s' "$id"; return 0
  fi
  id=$(api -X POST "$ADMIN_URL/v1/bucket" -d "{\"globalAlias\":\"$name\"}" 2>/dev/null \
       | sed -n 's/.*"id": *"\([0-9a-f]*\)".*/\1/p' | head -1 || true)
  if [ -z "$id" ]; then  # 409 等已存在形:回查
    id=$(curl -sS -H "$AUTH" "$ADMIN_URL/v1/bucket?globalAlias=$name" \
         | sed -n 's/.*"id": *"\([0-9a-f]*\)".*/\1/p' | head -1 || true)
  fi
  [ -n "$id" ] || die "建桶失败: $name"
  ok "桶建成: $name"
  printf '%s' "$id"
}

# ---------- 钥 ----------
# ensure_key <名> <键前缀>:打印 "id secret"(档案复用或新建;服务端旧钥删旧重建)
ensure_key() {
  local name="$1" pfx="$2" id sec resp oldid
  if [ -f "$CREDS" ]; then
    id=$(sed -n "s/^${pfx}_KEY_ID=//p" "$CREDS" 2>/dev/null || true)
    sec=$(sed -n "s/^${pfx}_KEY_SECRET=//p" "$CREDS" 2>/dev/null || true)
    if [ -n "$id" ] && [ -n "$sec" ]; then
      ok "钥复用(档案): $name"
      printf '%s %s' "$id" "$sec"; return 0
    fi
  fi
  oldid=$(curl -sS -H "$AUTH" "$ADMIN_URL/v1/keys" 2>/dev/null \
          | python3 -c "
import json,sys
try:
    for k in json.load(sys.stdin):
        if k.get('name') == '$name':
            print(k['accessKeyId']); break
except Exception: pass" || true)
  if [ -n "$oldid" ]; then
    api -X DELETE "$ADMIN_URL/v1/key?id=$oldid" >/dev/null 2>&1 || true
    log "删旧钥重建(密文不可再取): $name"
  fi
  resp=$(api -X POST "$ADMIN_URL/v1/key" -d "{\"name\":\"$name\"}")
  id=$(printf '%s' "$resp" | sed -n 's/.*"accessKeyId": *"\([^"]*\)".*/\1/p')
  sec=$(printf '%s' "$resp" | sed -n 's/.*"secretAccessKey": *"\([^"]*\)".*/\1/p')
  [ -n "$id" ] && [ -n "$sec" ] || die "建钥失败: $name"
  ok "钥建成: $name"
  printf '%s' "$id $sec"
}

# allow <bucketId> <keyId>:读写(owner 不给,桶生命周期归管理员)
allow() {
  api -X POST "$ADMIN_URL/v1/bucket/allow" \
    -d "{\"bucketId\":\"$1\",\"accessKeyId\":\"$2\",\"permissions\":{\"read\":true,\"write\":true,\"owner\":false}}" \
    >/dev/null
  ok "授权读写: 钥 $2 -> 桶 $(printf '%s' "$1" | cut -c1-8)"
}

log "初始化 garage(桶/钥/授权)"
FID=$(ensure_bucket "$FBUCKET")
SID=$(ensure_bucket "$S2BUCKET")
read -r S3_KEY_ID S3_KEY_SECRET <<< "$(ensure_key mesh-files S3)"
read -r S2_KEY_ID S2_KEY_SECRET <<< "$(ensure_key mesh-s2 S2)"
allow "$FID" "$S3_KEY_ID"
allow "$SID" "$S2_KEY_ID"

umask 077
{
  echo "S3_KEY_ID=$S3_KEY_ID"
  echo "S3_KEY_SECRET=$S3_KEY_SECRET"
  echo "S2_KEY_ID=$S2_KEY_ID"
  echo "S2_KEY_SECRET=$S2_KEY_SECRET"
} > "$CREDS"
ok "密钥档案: $CREDS(600)"
