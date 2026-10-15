#!/bin/sh
# tasks.sh v2.0.0 - goals 原语:全端 hst goal 互视互改(VIEW/OPERATE/DELIVER 三段式)
# 文法:goals [view [机|目标]] | set <机|目标> <文本> | <目标> <文本>(DELIVER)
# set 在目标格的 cwd 上执行(hst goal 是项目态;远端 = pending 流 + plugin action 唤醒,零 ssh 协议形)
set -u
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PRIMLIB="${PRIMLIB:-$(dirname "$SCRIPT_DIR")/primlib.sh}"
[ -f "$PRIMLIB" ] || PRIMLIB="$HOME/.local/bin/_primlib.sh"
. "$PRIMLIB"

case "${1:-}" in --llms) cat <<'EOF'
tasks@v2.3 - 舰队互操作·持久任务域:hst goal 全局遥控(引擎 hst;2.12.0 起 hst task)
读序:三段式 VIEW/OPERATE/DELIVER;目标文法同 agents
动词:view [机|目标] 格表+tasks/shared 事件+该机任务;set <目标> <文本>(只写不扰);<目标> <文本> [--force] = 格 cwd 上 set+事件+知会
语义:set 在目标格 cwd 执行(hst goal 是项目态);事件入 tasks/shared(互视+审计)
退出码:0/1/2
示例:
  tasks view hst_rs
  tasks s5_rs "稳定性评审收束后发版候总台裁"
EOF
exit 0 ;; esac
JSONF=""
for _a in "$@"; do [ "$_a" = "--json" ] && JSONF=1; done
VERB="${1:-view}"; shift 2>/dev/null || true
HB=$(prim_hb); S5=$(prim_s5bin)
HOST=$(prim_host)
[ -z "$HB" ] && { echo "goals: 本机无 herdr"; exit 1; }

task_remote_set() { # $1=machine $2=cwd $3=text —— 零 ssh 协议形(用户令 2026-10-13):pending 流 + plugin action 唤醒
  TID=$(date +%s%N 2>/dev/null || date +%s)
  printf '%s
' "$(prim_host)|$3|$2|$TID" | "$S5" append "tasks/pending/$1" >/dev/null 2>&1     || { echo "tasks: pending 流写败" >&2; return 1; }
  "$HB" --machine "$1" plugin action invoke apply --plugin tasks >/dev/null 2>&1
}
goal_show_on() { # $1=machine $2=cwd —— 远读走 tasks/shared 事件流(协议面;精确实时值候对端 apply 自报)
  if [ -z "$1" ] || [ "$1" = "local" ]; then
    cd "$2" 2>/dev/null && hst goal show 2>&1 | head -8 || echo '(该目录无 goal 或无 hst)'
  else
    "$S5" tail tasks/shared 2>/dev/null | grep "node=$1" | tail -2 || echo "(远机暂无事件,候其 apply 自报)"
  fi
}
event() { # $1=node $2=cwd $3=by $4=text(事件行;写失败即败)
  ESC=$(printf '%s' "$4" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read().strip()))')
  printf '%s\n' "{\"ts":"$(date -Iseconds)","node":"$1","cwd":"$2","by":"$3","goal\":${ESC}}" \
    | "$S5" append tasks/shared >/dev/null 2>&1
}

case "$VERB" in
  view|"")
    prim_agents_table ""
    echo "-- tasks/shared 最近事件:"
    "$S5" tail tasks/shared 2>/dev/null | tail -8
    if [ -n "${1:-}" ] && [ "$1" != "-" ]; then
      T="$1"; R=$(prim_lookup "$T") || exit 1; M=${R%%|*}; P=${R#*|}
      MM="$M"; [ -z "$MM" ] && MM=local
      CWD=$(prim_pane_cwd "$M" "$P")
      if [ -n "$CWD" ]; then
        echo "-- ${MM}:${P} 的 goal(cwd=${CWD}):"
        goal_show_on "$MM" "$CWD"
      else
        echo "-- ${MM} 机的 goal(家目录):"
        goal_show_on "$MM" "\$HOME"
      fi
    fi ;;
  set)
    T="$1"; TEXT="$2"
    R=$(prim_lookup "$T") || exit 1; M=${R%%|*}; P=${R#*|}
    MM="$M"; [ -z "$MM" ] && MM=local
    CWD=$(prim_pane_cwd "$M" "$P"); CWD="${CWD:-\$HOME}"
    if [ -z "$M" ] || [ "$M" = "local" ]; then
      ESC=$(printf '%s' "$TEXT" | sed "s/'/'\''/g"); (cd "$CWD" 2>/dev/null || cd "$HOME"; hst goal set "$ESC" >/dev/null 2>&1) || { echo "tasks: 本机 set 失败" >&2; exit 1; }
    else
      task_remote_set "$M" "$CWD" "$TEXT" || { echo "tasks: 远端协议投递失败(${M})" >&2; exit 1; }
    fi
    event "$MM" "$CWD" "$HOST" "$TEXT" || { echo "goals: set 已成但事件流写败(整单判败)"; exit 1; }
    echo "goals: 已设 ${MM} ${CWD} →「${TEXT}」(事件入 tasks/shared)" ;;
  *)
    # DELIVER:goals <目标> <文本> [--force]
    [ $# -lt 1 ] && { echo "tasks: 用法见 --llms(DELIVER 参数不足)" >&2; exit 2; }
    T="$VERB"; TEXT="$1"; FORCE=""
    [ "${2:-}" = "--force" ] && FORCE="--force"
    R=$(prim_lookup "$T") || exit 1; M=${R%%|*}; P=${R#*|}
    prim_gate_deliver "$M" "$P" "$FORCE" || { prim_defer "$P" tasks "任务「${TEXT}」待设(--force 重发)"; exit 1; }
    [ "$FORCE" = "--force" ] && prim_audit_force "${M:+$M:}$P" tasks
    SRC=$(prim_caller_addr)
    MM="$M"; [ -z "$MM" ] && MM=local
    CWD=$(prim_pane_cwd "$M" "$P"); CWD="${CWD:-\$HOME}"
    if [ -z "$M" ] || [ "$M" = "local" ]; then
    ESC=$(printf '%s' "$TEXT" | sed "s/'/'\''/g"); (cd "$CWD" 2>/dev/null || cd "$HOME"; hst goal set "$ESC" >/dev/null 2>&1) || { echo "tasks: 本机 set 失败" >&2; exit 1; }
  else
    task_remote_set "$M" "$CWD" "$TEXT" || { echo "tasks: 远端协议投递失败(${M})" >&2; exit 1; }
  fi
    event "$MM" "$CWD" "$HOST" "$TEXT" || { echo "tasks: set 已成但事件流写败" >&2; exit 1; }
    MSG="[tasks] ${SRC} 将你所在项目的 goal 设为:「${TEXT}」
src=${SRC} cwd=${CWD}
取用:cd ${CWD} && hst goal show"
    if [ -n "$M" ] && [ "$M" != "local" ]; then
      "$HB" --machine "$M" agent prompt "$P" "$MSG" --wait --until working --timeout 15000 >/dev/null 2>&1 \
        && { echo "tasks: 已设并知会 ${M}:${P}"; [ -n "$JSONF" ] && printf '{"ok":true,"data":{"target":"%s:%s","cwd":"%s"},"meta":{"command":"tasks"}}
' "$M" "$P" "$CWD"; } || echo "tasks: 已设,知会失败 ${M}:${P}" >&2
    else
      "$HB" agent prompt "$P" "$MSG" --wait --until working --timeout 15000 >/dev/null 2>&1 \
        && { echo "tasks: 已设并知会 ${P}"; [ -n "$JSONF" ] && printf '{"ok":true,"data":{"target":"local:%s","cwd":"%s"},"meta":{"command":"tasks"}}
' "$P" "$CWD"; } || echo "tasks: 已设,知会失败 ${P}" >&2
    fi ;;
esac
