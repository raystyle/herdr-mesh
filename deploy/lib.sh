#!/usr/bin/env bash
# 公共函数(部署与冒烟脚本共享)
set -uo pipefail

# 约定:log/ok 走 stderr(stdout 留给函数返回值管道,如 $(ensure_bucket ...))
log()  { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*" >&2; }
ok()   { printf '[%s] OK  %s\n' "$(date +%H:%M:%S)" "$*" >&2; }
fail() { printf '[%s] FAIL %s\n' "$(date +%H:%M:%S)" "$*" >&2; }
die()  { fail "$*"; exit 1; }

need() { command -v "$1" >/dev/null 2>&1 || die "缺依赖: $1(先装再用)"; }

# wait_http <url> [超时秒] [期望响应子串,可空]
wait_http() {
  local url="$1" timeout="${2:-60}" want="${3:-}"
  local i=0 out
  while [ "$i" -lt "$timeout" ]; do
    if out=$(curl -fsS --max-time 3 "$url" 2>/dev/null); then
      if [ -z "$want" ] || printf '%s' "$out" | grep -q "$want"; then
        printf '%s' "$out"; return 0
      fi
    fi
    sleep 2; i=$((i + 2))
  done
  die "等待超时: $url ($timeout s)"
}

# load_env <env文件>:占位值未换即拒
load_env() {
  local f="$1"
  [ -f "$f" ] || die "缺 $f(复制 env.example 为 env 并填真值)"
  # shellcheck disable=SC1090
  . "$f"
  local v
  for v in GARAGE_RPC_SECRET GARAGE_ADMIN_TOKEN STORE_NODE_SSH BASIN_NAME; do
    case "${!v:-}" in
      ""|"<"*|"__openssl_rand_hex_32__") die "env 未填真值: $v";;
    esac
  done
}

# rand_hex [字节]: openssl 生成 hex 秘密
rand_hex() { openssl rand -hex "${1:-32}"; }
