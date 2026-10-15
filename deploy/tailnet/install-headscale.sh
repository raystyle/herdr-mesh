#!/usr/bin/env bash
# tailnet 控制面(headscale)一键部署 + 建用户 + 预发 authkey
# 用法: deploy/tailnet/install-headscale.sh [控制面域名]
# 前置:docker;8080(裸)/3478(UDP stun)可达;443 由你的反代终结 TLS 转 8080。
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/../lib.sh"
need docker

DOMAIN="${1:?用法: install-headscale.sh <控制面域名>}"
ROOT=/opt/headscale

log "落模板(存在即跳,改占位符)"
sudo mkdir -p "$ROOT/data"
for f in config.yaml derpmap.yaml policy.hujson; do
  if [ ! -f "$ROOT/$f" ]; then
    sudo cp "$HERE/$f" "$ROOT/$f"
  fi
done
sudo sed -i "s|<控制面域名>|$DOMAIN|g" "$ROOT/config.yaml" "$ROOT/derpmap.yaml"

log "起容器(unless-stopped)"
sudo docker inspect headscale >/dev/null 2>&1 || sudo docker run -d --name headscale --restart unless-stopped   -v "$ROOT":/etc/headscale -v "$ROOT/data":/var/lib/headscale   headscale/headscale:latest serve
sudo docker start headscale >/dev/null 2>&1 || true

log "等健康(容器内 9090 metrics)"
for i in $(seq 1 30); do
  if sudo docker exec headscale wget -qO- http://127.0.0.1:9090/metrics >/dev/null 2>&1; then break; fi
  sleep 2
done

log "建用户 + 预发 authkey(24h)"
sudo docker exec headscale headscale users create mesh 2>/dev/null || log "用户已在"
KEY=$(sudo docker exec headscale headscale preauthkeys create --user mesh --expiration 24h --reusable 2>/dev/null | tail -1)

ok "控制面就绪: https://$DOMAIN(反代 443 -> 8080,stun 3478/udp)"
if [ -n "${KEY:-}" ]; then
  echo "节点接入(headscale up 会弹浏览器,或直接用 authkey):"
  echo "  sudo tailscale up --ssh --login-server=https://$DOMAIN --hostname=<节点名> --authkey=$KEY"
  echo "authkey 也可稍后: docker exec headscale headscale preauthkeys create --user mesh --expiration 24h"
fi
