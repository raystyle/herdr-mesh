#!/usr/bin/env bash
# 一键全链部署:存储面 -> 各节点面 -> 全链冒烟
# 用法: deploy/install-mesh.sh [env文件]
# 运行处:部署机(能 ssh 到 store-node 与所有 AGENT_NODES)。
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ENVF="${1:-$HERE/env}"
CREDS="$HERE/.store-credentials"

log "一、存储面"
bash "$HERE/store/install-store.sh" "$ENVF"

log "二、节点面(逐台)"
# shellcheck disable=SC1090
. "$ENVF"
for NODE in $AGENT_NODES; do
  log "-- $NODE"
  ssh "$NODE" "mkdir -p ~/mesh-deploy/store ~/mesh-deploy/node"
  scp -q "$HERE/lib.sh" "$NODE:mesh-deploy/"
  scp -q "$HERE/node/install-node.sh" "$NODE:mesh-deploy/node/"
  scp -q "$ENVF" "$NODE:mesh-deploy/env"
  scp -q "$CREDS" "$NODE:mesh-deploy/.store-credentials"
  ssh "$NODE" "bash ~/mesh-deploy/node/install-node.sh ~/mesh-deploy/env ~/mesh-deploy/.store-credentials"
  ssh "$NODE" "rm -rf ~/mesh-deploy"
done

log "三、全链冒烟"
bash "$HERE/../smoke/smoke.sh" "$ENVF" "$CREDS"
ok "部署完成,冒烟全绿"
