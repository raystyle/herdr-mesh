#!/bin/sh
# apply.sh v0.2.0 - tasks 原语对端动作:取 tasks/pending/<本机> 最新意图 → cd <cwd> && hst task set --agent → 回执 tasks/shared
# 零 ssh 协议形(用户令 2026-10-13:原语不走 ssh):数据面 s5 pending 流,控制面 herdr --machine plugin action 唤醒
set -u
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PRIMLIB="${PRIMLIB:-$(dirname "$SCRIPT_DIR")/../primlib.sh}"
[ -f "$PRIMLIB" ] || PRIMLIB="$HOME/.local/bin/_primlib.sh"
. "$PRIMLIB" 2>/dev/null || true

HOST=$(hostname -s 2>/dev/null || hostname)
S5=$(prim_s5bin 2>/dev/null); HB=$(prim_hb 2>/dev/null)
[ -z "$S5" ] && { echo "tasks-apply: 本机无 s5" >&2; exit 1; }

# 取最新 pending 事件(body = by|text|cwd|id|agent 五段竖线形)
LAST=$("$S5" tail "tasks/pending/$HOST" 2>/dev/null | tail -1)
[ -z "$LAST" ] && { echo "tasks-apply: 无待执行意图"; exit 0; }
BODY=$(printf '%s' "$LAST" | python3 -c "import json,sys; print(json.load(sys.stdin).get('body',''))" 2>/dev/null)
BY=$(printf '%s' "$BODY" | cut -d'|' -f1)
TEXT=$(printf '%s' "$BODY" | cut -d'|' -f2)
CWD=$(printf '%s' "$BODY" | cut -d'|' -f3)
TID=$(printf '%s' "$BODY" | cut -d'|' -f4)
AGENT=$(printf '%s' "$BODY" | cut -d'|' -f5)
AGENT=${AGENT:-claude}
[ -z "$TEXT" ] && { echo "tasks-apply: 意图空" >&2; exit 1; }

# 本机执行(hst 2.15.0 形:task set --agent 按格 agent 隔离;goal 腿已清)
ESC=$(printf '%s' "$TEXT" | sed "s/'/'\\\\''/g")
if [ -n "$CWD" ] && [ "$CWD" != "-" ]; then
  cd "$CWD" 2>/dev/null || cd "$HOME"
fi
export PATH="$HOME/.local/bin:$PATH"
hst task set --agent "$AGENT" "$ESC" >/dev/null 2>&1 || { echo "tasks-apply: 本机 set 失败" >&2; exit 1; }

# 回执(同 id 入 tasks/shared,幂等锚)
printf '%s\n' "$(date -Iseconds)|node=$HOST|cwd=${CWD:-HOME}|by=$BY|id=$TID|applied=$TEXT" | "$S5" append tasks/shared >/dev/null 2>&1
echo "tasks-apply: 已执行 id=$TID by=$BY cwd=${CWD:-HOME}"
