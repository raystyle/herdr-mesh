#!/usr/bin/env bash
# 全链冒烟:从部署机跑,逐节验收 存储面 -> 节点面 -> 跨节点投递
# 用法: smoke/smoke.sh <env文件> <credentials文件>
# 全绿退出 0;任一节失败退出 1 并停在该节。
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/../deploy/lib.sh"
load_env "${1:?用法: smoke.sh <env> <credentials>}"
CREDS="${2:?用法: smoke.sh <env> <credentials>}"
. "$CREDS"

STORE="$STORE_NODE_SSH"
PASS=0; FAIL=0

# check <名称> <命令...>:命令退出 0 = 过
check() {
  local name="$1"; shift
  log "验: $name"
  if "$@" >/dev/null 2>&1; then
    ok "$name"; PASS=$((PASS+1))
  else
    fail "$name"; FAIL=$((FAIL+1))
  fi
}

# ---------- 一、存储面 ----------
log "== 一、存储面($STORE)=="
STORE_IP=$(ssh "$STORE" "hostname -I | awk '{print \$1}'")
S3="http://${STORE_IP}:${GARAGE_S3_PORT:-3900}"
ADMIN="http://${STORE_IP}:${GARAGE_ADMIN_PORT:-3903}"
S2="http://${STORE_IP}:${S2_PORT:-8090}"

check "garage 健康(admin /health)"        curl -fsS "$ADMIN/health"
check "garage 版本(admin /status)"        bash -c "curl -fsS '$ADMIN/status' -H 'Authorization: Bearer $GARAGE_ADMIN_TOKEN' | grep -q garageVersion"
check "文件桶在(${S5_BUCKET})"            bash -c "curl -fsS '$ADMIN/v1/bucket?globalAlias=${S5_BUCKET}' -H 'Authorization: Bearer $GARAGE_ADMIN_TOKEN' | grep -q '\"id\"'"
check "流后备桶在(${S2_BUCKET})"          bash -c "curl -fsS '$ADMIN/v1/bucket?globalAlias=${S2_BUCKET}' -H 'Authorization: Bearer $GARAGE_ADMIN_TOKEN' | grep -q '\"id\"'"
check "s2-lite 健康(/health)"             bash -c "curl -fsS '$S2/health' | grep -q OK"
check "basin 在(${BASIN_NAME})"           bash -c "curl -fsS '$S2/v1/basins' | grep -q '\"$BASIN_NAME\"'"

# ---------- 二、节点面(逐节点)----------
log "== 二、节点面 =="
for NODE in $AGENT_NODES; do
  log "-- 节点 $NODE"
  check "$NODE herdr 版本"        ssh "$NODE" "herdr --version"
  check "$NODE herdr server 活"   ssh "$NODE" "pgrep -f 'herdr server'"
  check "$NODE s5 版本"           ssh "$NODE" "s5 --version"
  check "$NODE prim 三命令"       ssh "$NODE" "command -v agents && command -v shares && command -v streams"
  check "$NODE s5 可用(put+get)" ssh "$NODE" "s5 put - smoke-$NODE-probe <<< hello && s5 get smoke-$NODE-probe | grep -qx hello"
  check "$NODE 流可写(append)"    ssh "$NODE" "s5 append smoke/probe <<< \"\$(hostname -s)|probe\""
done
LAST_NODE=$(echo "$AGENT_NODES" | awk '{print $NF}')
FIRST_NODE=$(echo "$AGENT_NODES" | awk '{print $1}')

# ---------- 三、跨节点(投递与流)----------
log "== 三、跨节点 =="
if [ "$FIRST_NODE" != "$LAST_NODE" ]; then
  check "跨机流互见(tail 读对端 append)" \
    ssh "$FIRST_NODE" "s5 append smoke/xnode <<< 'xnode-probe' && ssh $LAST_NODE s5 tail smoke/xnode -n 5 | grep xnode-probe"
else
  log "(单节点部署,跳过跨机节)"
fi
check "herdr 机册互通(machine list 出对端)" \
  ssh "$LAST_NODE" "herdr machine list | grep -q '$FIRST_NODE'"
check "agents 全局面(本机格表)"  ssh "$LAST_NODE" "agents view"
check "streams 全局面"           ssh "$LAST_NODE" "streams view"

# ---------- 收尾 ----------
log "== 结果: $PASS 过 / $FAIL 败 =="
[ "$FAIL" -eq 0 ] && ok "冒烟全绿" || { fail "有败项(见上)"; exit 1; }
