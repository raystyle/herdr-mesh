"""prim CLI - 五原语命令入口(v3 python 形)

文法(CONTRACT 五d):<命令> [全局旗标] <动词> [动词旗标] [位置参数...]
全局七旗标:--help -h --llms --format --json --full-output --filter-output --schema
投递:to <id> [域操作数...] [--force];-- 逃生口
"""
from __future__ import annotations
import json
import subprocess
import sys
import os
import time
from . import core
from .core import (die, emit_ok, eprint, herdr, herdr_run, herdr_json, s5,
                   resolve, host_label, deliver_prompt, gate, pane_cwd,
                   _agents_of, _machine_labels, target_status)


def subprocess_run(cmd: list[str], **kw):
    return subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", **kw)

GLOBAL_FLAGS = {"--help": "help", "-h": "help", "--llms": "llms", "--json": "json",
                "--format": "format", "--full-output": "full", "--filter-output": "filter",
                "--schema": "schema"}
DELIVER_FLAG = "--force"

# ---------- 解析层(POSIX/GNU 对齐) ----------

def parse(argv: list[str]) -> tuple[dict, str | None, list[str]]:
    """扫描全部词:全局旗标任意槽抽出;-- 逃生;剩余 = [动词?] + 位置参数。"""
    g: dict = {}
    rest: list[str] = []
    escape = False
    i = 0
    while i < len(argv):
        a = argv[i]
        if escape:
            rest.append(a); i += 1; continue
        if a == "--":
            escape = True; i += 1; continue
        if a in GLOBAL_FLAGS:
            k = GLOBAL_FLAGS[a]
            if k == "format" and i + 1 < len(argv):
                g[k] = argv[i + 1]; i += 2; continue
            if k == "filter" and i + 1 < len(argv):
                g[k] = argv[i + 1]; i += 2; continue
            g[k] = True; i += 1; continue
        if a == DELIVER_FLAG:
            g["force"] = True; i += 1; continue
        rest.append(a); i += 1
    verb = rest[0] if rest and not rest[0].startswith("-") else None
    pos = rest[1:] if verb else rest
    return g, verb, pos

def setup(cmd: str, g: dict):
    core.CMD_NAME = cmd
    core.JSON_MODE = bool(g.get("json") or g.get("format") == "json")
    core.FORCE = bool(g.get("force"))

def handle_globals(g: dict, manual: str) -> bool:
    if g.get("help"):
        print(manual); sys.exit(0)
    if g.get("llms"):
        print(manual); sys.exit(0)
    return False

# ---------- 手册(单源) ----------

def _pkg_ver() -> str:
    """--llms 头版本单源:包元数据(C4 票,禁手写漂移)。"""
    try:
        from importlib.metadata import version as _v
        return _v("prim")
    except Exception:
        return "v?"


def manual(cmd: str) -> str:
    m = {
        "agents": f"""agents@{_pkg_ver()} - 消息域:全局 pane 操作器(隐式路由,任何端点可用)
文法:agents [全局旗标] <动词> [动词旗标] [位置参数];裸调用 = view
全局旗标:--help -h --llms --json --format <fmt> --full-output --filter-output <pat> --schema --force(投递)
动词:view [host];machines;list [机];ws|workbenches [机](工作台清点:home+~/repos/* 仓+origin);yolo [--audit]|yolo <id> [--yes](四家 CLI 检测/冷翻);read <id> [--lines N] [--timeout S];keys <id> <键>;
  to <id> <文本> [--force](投递即镜像 dm 流,回信事件道:wait 收)
  wait [--from <id>] [--timeout S](阻塞等新入站消息,到件即返;引擎级轮询,agent 不再盲等)
  inbox [--from <id>](非阻塞收件单:dm 流入站消息清单)
  mode <dnd|away|online> [until](presence 走 shares 键);
  start <名> --kind <类> [--pane 格] [--cwd DIR] [--machine 机];
  ws <label> [--cwd DIR] [--machine 机]|ws list [机]|ws close <台> [机];
  shell <机> <仓路径>(开台 shell 回 root 格);dev <机> <仓路径> [--kind 类](开台+起 agent);
  split <id> [--direction right|down];tab <list [机]|create <机>|close <机:tab>>;
  zoom <id>;close <id>(关格零击杀:agent /exit 优雅退后 shell exit,格自消);
  wt [机] [--title 名](win 专属:本窗开 tab 显该机窗格视图);
  trust(信任屏放行);sync(机册面);reload <id>(同格同 session 重进,重载技能与插件)
id:裸名(全局,投递回信用bare alias)|机:名或格|local:格;裸 pane id 非法;信封 from 机器段 = host_label
示例:
  agents view
  agents read evo-claude --lines 20
  agents to evo-claude "评审请求已递" --json
  agents dev node-a ~/repos/myrepo --kind grok""",
        "machines": f"""machines@{_pkg_ver()} - 机册域:herdr machine 封装(第九原语;ADR-0007 由 nodes 更名,nodes 别名已淘汰)
动词:view/list(册表+可达)/ status [名](全量或单机)/
  add <ssh-target> [--label <名>] [--remote-session <名>](注册新节点,herdr 自动装远端并起 server)/
  rename <名> --label <新名> / remove <名> / enable <名> / disable <名> / reconnect <名>/
  runtime [view|init|check|install|update|doctor|heal|config] [工具...](agent 运行时环境面,
  骑 ark;栈真源 = 仓根 runtimes.toml 仓 agent 自定;--machine <节点> 跨机经 ssh)/
  run <节点> <格> <命令...>(格内跑命令)/ close <节点> <格>(直关格)/
  pane <节点> <herdr pane 子面...>(list/get/read/split 直透)
寻址:label 或 profile-id 皆收(label 优先);机册真源在 herdr
示例:
  machines view
  machines add user@10.0.0.7 --label node-b
  machines disable node-b
  machines reconnect node-a
""",
        "mcps": """mcps@v3 - MCP 域:通用 MCP 客户端(第八原语,出站;引擎 mcp2cli)
文法:mcps [全局旗标] <动词> [位置参数];裸调用 = view
动词:view [目标](在册表+健康)/ tools <目标>(列 tools)/
  call <目标> <tool> [--arg k=v]... [--arg-json k=<json>]...(调用;值字符串形透传)/
  add <名> --url <URL> [--note <注>]/ remove <名>
注册表:~/.config/mcps/targets.yaml(名->url;MCPS_REGISTRY env 覆盖)
超时:--timeout <s> 覆盖;view/tools 默认 10s、call 120s,上限 600
示例:
  mcps view
  mcps tools my-mcp
  mcps call my-mcp shell --arg cmd=whoami --arg wait=true
  mcps call my-mcp spawn --arg-json 'argv=["notepad"]'
  mcps add my-mcp --url http://10.0.0.5:9881/mcp --note 试""",
        "shares": f"""shares@v3 - 文件域:S3 中转(引擎 s5;内容哈希键)
动词:view;put <文件>;get <键> [-o|--output 名];to <id> <文件> [--force](=上架+模板知会)
示例:
  shares put report.md
  shares to hst_rs report.md --json""",
        "streams": """streams@v3 - 流域:S2 持久流(引擎 s5;room 即房间,一等概念)
动词:rooms(列房间);room <room>(read room,-f 活跟随)/ room <room> <消息> [--file <文件> [--lines N:M]](speak room或传日志切片);
  dm <对方别名> <消息> [--file <文件> [--lines N:M]](DM lane,流名按双别名排序自动定);
  view [流名] [--from <seq>|--resume] [-n N] [-f](活跟随,Ctrl+C 退 130);append <流> <消息>(或 stdin 管道:cat x | streams append <流>,不加 host 前缀);to <id> <流> <消息> [--force]
示例:
  streams rooms
  streams room fleet
  streams room gateway-logging 四方合研-新证据入档
  streams room gateway-logging 日志请看 --file app.log --lines 50-62
  streams dm research-grok-1 私信验证
  cat build.log | streams append room/build
  streams to evo-claude fleet 回执-批X完成""",
        "tasks": f"""tasks@v3 - 持久任务域:hst task 全局遥控(引擎 hst)
动词:view [host](实时任务面:fleet 状态总览加本机各仓 hst task show 直读;远机任务经 agents read <id> 看屏);
  set <id> <文本>;to <id> <文本> [--force](=set+知会)
示例:
  tasks view
  tasks to s5_rs "评审收束后发版\"""",
        "pipes": f"""pipes@v3 - 管道域:tailcat 实时(本机收对方发;管道常驻至 close)
动词:view [host];open;close <addr|pid>;send <addr>(recipient:连管道发数据,stdin 直通);to <id> [--force](=open+模板知会,取用行 pipes send)
示例:
  pipes view node-a
  pipes to evo-claude""",
        "ports": f"""ports@v3 - 端口域:任意节点端口转发映射(引擎 tailcat serve;映射常驻至 close)
动词:view [host];open <spec>(spec = 8080,8443 端口表 / 5555:IP:5555 服务侧映射,serve 面被服务端口,非客户端监听 / all / exit-node);close <addr|pid>;fwd <addr> <local>:<remote-port>(recipient: local listener, 0 = free port, Ctrl+C to stop);to <id> <spec> [--force](=open+模板知会,取用行 ports fwd 全端口枚举)
示例:
  ports view node-a
  ports open 8123
  ports open 5555:10.2.200.213:5555
  ports to evo-claude 8123""",
        "ctxs": """ctxs@v3 - 对话历史域:agent 请求全链检索(引擎 ClickHouse gw_logs;与 agents read 分工:read=实时屏,ctxs=历史档案)
动词:view [agent] [--limit N](最近请求头行:时间/模型/token/耗时/request_id);
  show <request_id> [--around <词>] [--window N](全链;--around 只出命中块±N 邻块,命中块为命中点居中 3000 字);
  search <词> [--term <词>]... [--limit N](跨请求全文,多词 OR;每行带命中片段 snip)
窗口:head 365 天,gwlog 正文 180 天;词至少 2 字符(UTF-8 计)
示例:
  ctxs view
  ctxs show 0192a0f0-xxxx --around "挂死" --window 1
  ctxs search "panic"
  ctxs search --term 杀树 --term ensure_ascii""",
    }
    return m.get(cmd, "")

# ---------- agents 动词实现 ----------

def _val(pos: list[str], flag: str, default: str = "") -> str:
    """动词旗标取值:--flag 值 任意槽。"""
    if flag in pos:
        i = pos.index(flag)
        if i + 1 < len(pos):
            return pos[i + 1]
    for p in pos:
        if p.startswith(flag + "="):
            return p.split("=", 1)[1]
    return default

def _json_field(text: str, *keys: str) -> str:
    """嵌套 JSON 里取字段(逐层下钻),失败空串。"""
    try:
        d = json.loads(text)
        for k in keys:
            d = d.get("result", d) if isinstance(d, dict) and "result" in d and k not in d else d
            d = d.get(k, "")
        return str(d or "")
    except Exception:
        return ""

def resolve_tab(id_str: str) -> tuple[str, str]:
    """tab id 解析:机:tabid(缺省 local)。"""
    if ":" in id_str:
        m, tid = id_str.split(":", 1)
        if m == "local":
            return "local", tid
        if m in _machine_labels():
            return m, tid
        die("not_found", f"机器「{m}」不在册")
    return "local", id_str

def _agents_trust(machine: str | None):
    """信任屏放行:blocked/unknown 格扫屏按键(shell v2.8 判标同源移植)。"""
    ags = _agents_of(machine)
    pending = [a for a in ags if a.get("agent_status", "") in ("blocked", "unknown")]
    if not pending:
        print("agents trust: 无待放行格")
        return
    m_label = machine or "local"
    for a in pending:
        pane = a.get("pane_id", "")
        r = herdr_run(None if m_label in ("", "local") else m_label,
                      "agent", "read", pane, "--source", "visible")
        screen = r.stdout or ""
        acted = False
        if "Yes, I trust this folder" in screen:
            herdr_run(machine, "agent", "send-keys", pane, "down")
            time.sleep(1)
            herdr_run(machine, "agent", "send-keys", pane, "enter")
            print(f"agents trust: {pane} claude 已下移确认(2.x 形)")
            acted = True
        elif "Yes, allow external imports" in screen or ("Enter to confirm" in screen and "Esc to cancel" in screen):
            herdr_run(machine, "agent", "send-keys", pane, "down")
            time.sleep(1)
            herdr_run(machine, "agent", "send-keys", pane, "enter")
            print(f"agents trust: {pane} claude 确认屏放行(通用形)")
            acted = True
        elif "Do you trust the files in this folder" in screen:
            herdr_run(machine, "agent", "send-keys", pane, "enter")
            print(f"agents trust: {pane} claude 已确认(经典形)")
            acted = True
        elif "Trust this folder?" in screen or "Do you trust the contents of this directory" in screen:
            herdr_run(machine, "agent", "send-keys", pane, "enter")
            print(f"agents trust: {pane} codex 已确认")
            acted = True
        elif "Trust the authors of this folder" in screen:
            herdr_run(machine, "agent", "send-keys", pane, "y")
            time.sleep(1)
            herdr_run(machine, "agent", "send-keys", pane, "enter")
            print(f"agents trust: {pane} grok 已答 y")
            acted = True
        if not acted:
            print(f"agents trust: {pane} 无已知信任屏(文案变体,人工核)")

def _blocked_after_start(m: str, pane: str, kind: str, wait_s: int = 30) -> dict | None:
    """启动后阻塞检测(用户令 2026-10-17):轮询屏面到 wait_s;命中对话框 = 返回 {marker, action, cta}。
    alt-screen 读空(claude TUI 主屏)不算可投,靠 status + tail markers;返回 None = 无阻塞。"""
    import time as _t
    from .core import TUI_DIALOGS, FORCE
    if FORCE:
        return None
    hm = None if m in ("", "local") else m
    markers = TUI_DIALOGS.get(kind, ()) + TUI_DIALOGS.get("claude", ())
    deadline = _t.time() + wait_s
    while _t.time() < deadline:
        r = herdr_run(hm, "agent", "read", pane, "--source", "visible", "--lines", "40", timeout=15)
        screen = r.stdout or ""
        if screen.strip():
            tail = chr(10).join(screen.splitlines()[-12:])

            hit = next((mk for mk in markers if mk in tail), None)
            if hit:
                return {"marker": hit, "kind": kind}
        _t.sleep(2.5)
    return None


def _dismiss_block_hint(hit: dict) -> list[str]:
    """阻塞 CTA 提示(不自动按键:信任屏须人裁)。"""
    return [
        f"agents: 启动后检测到阻塞对话框({hit['marker'][:40]})",
        "下一步:人工放行(下箭头选 Yes + Enter),或 agents to <id> --force 绕门控投递指令",
    ]


def _shell_only_panes(machine: str) -> list[dict]:
    """扫 pane 面找无 agent 的空格(用户令 2026-10-17:所有 pane 必须有 agent,空 pane = 异常态)。"""
    m = None if machine in ("", "local") else machine
    r = herdr_json(m, "pane", "list", timeout=20)
    panes = r.get("result", {}).get("panes") if isinstance(r, dict) else None
    if not panes:
        return []
    return [p for p in panes if not p.get("agent")]


# 自制 TUI 屏面判标(非 agent 但有活跃程序,不是空壳)
TUI_MARKERS: tuple[str, ...] = (
    "数据链路", "  #  Help", "q 退出", "q quit", "│ File │", "NCURSES",
)


def _is_tui_pane(machine: str, pane: dict) -> bool:
    """空 pane 再判:屏面有 TUI 特征 = 自制监控/操作台,非异常态。"""
    m = None if machine in ("", "local") else machine
    pid = pane.get("pane_id", "")
    r = herdr_run(m, "pane", "read", pid, "--source", "visible", "--lines", "20", timeout=10)
    tail = "\n".join((r.stdout or "").splitlines()[-20:])
    return any(mk in tail for mk in TUI_MARKERS)


def agents_view(machine: str | None):
    rows = _agents_of(machine or None)
    if not machine:
        rows = [("local", a) for a in rows]
        dead = []
        strays = []
        # local 首拍已入行;此循环只走远程机(local 再遍 = 行双列,2026-10-17 实测根修)
        for lab in _machine_labels():
            got = _agents_of(lab, timeout=12)
            if not got:
                dead.append(lab)
                continue
            rows += [(lab, a) for a in got]
            strays += [(lab, p) for p in _shell_only_panes(lab)]
        strays = [(l, p) for l, p in strays if not _is_tui_pane(l, p)]
        print(f"{'HOST':<12} {'NAME':<12} {'PANE':<8} {'STATUS':<8} {'KIND':<7} CWD")
        for host, a in rows:
            print(f"{host:<12} {(a.get('name') or '-'):<12} {a.get('pane_id',''):<8} {a.get('agent_status',''):<8} {(a.get('agent') or '-'):<7} {a.get('cwd','')}")
        if strays:
            eprint(f"agents: ⚠ 空 pane {len(strays)} 格(异常态:pane 须有 agent):")
            for lab, p in strays:
                eprint(f"  {lab}:{p.get('pane_id')} cwd={p.get('cwd')}(desks close {lab} {p.get('pane_id')} 或 agents dev 补 agent)")
        if dead:
            eprint(f"agents: 不可达机 {len(dead)} 台跳过({', '.join(dead)});单机详查:agents view <host>")
    else:
        for a in rows:
            print(f"{a.get('pane_id',''):<8} {(a.get('name') or '-'):<12} {a.get('agent_status',''):<8} {a.get('cwd','')}")
        strays = _shell_only_panes(machine)
        if strays:
            eprint(f"agents: ⚠ 空 pane {len(strays)} 格(异常态):")
            for p in strays:
                eprint(f"  {machine}:{p.get('pane_id')} cwd={p.get('cwd')}")

def desk_view(machine: str | None):
    """desk view:拓扑面真视图(ADR-0007 desk/agents 分职)。数据 = herdr pane list 全格(含非 agent 格),
    按 窗台(workspace, w 编号) -> tab -> 工位(pane) 三层分组;焦点工位 ▍ 标记(TUI 焦点定式);活动列 = terminal_title。
    术语定谳(2026-10-25 用户令):工位/窗格 = pane;工作台/窗台 = workspace(w)。
    与 agents view 分工:agents view = 消息面 agent 表(名/态/类/cwd),desk view = 拓扑(全量工位+活动)。"""
    dead: list[str] = []
    targets: list[tuple[str, str | None]] = [("local", machine or None)] if machine else [("local", None)] + [(lab, lab) for lab in _machine_labels()]
    sections: list[tuple[str, list[dict]]] = []
    for label, m in targets:
        try:
            d = herdr_json(m, "pane", "list", timeout=12)
        except SystemExit:
            dead.append(label)
            continue
        panes = d.get("result", {}).get("panes", []) if isinstance(d, dict) else []
        if not panes:
            if label != "local":
                dead.append(label)
            continue
        sections.append((label, panes))
    json_rows: list[dict] = []
    lines: list[str] = []
    for label, panes in sections:
        ws_map: dict[str, dict[str, list[dict]]] = {}
        for p in panes:
            ws_map.setdefault(p.get("workspace_id", "?"), {}).setdefault(p.get("tab_id", "?"), []).append(p)
        for ws, tabs in sorted(ws_map.items()):
            n_panes = sum(len(v) for v in tabs.values())
            lines.append(f"{'' if label == 'local' else label + ':'}{ws} 窗台 {len(tabs)} tab {n_panes} 工位")
            for tab, plist in sorted(tabs.items()):
                for p in plist:
                    focus = "▍" if p.get("focused") else " "
                    kind = p.get("agent") or "-"
                    st = p.get("agent_status") or "?"
                    title = (p.get("terminal_title_stripped") or "")[:38]
                    lines.append(f"  {tab.split(':')[-1]:<3} {p.get('pane_id', '').split(':')[-1]:<4}{focus}{kind:<7}{st:<8}{title}")
                    json_rows.append({"machine": label, "workspace": ws, "tab": tab, "pane": p.get("pane_id", ""),
                                      "focused": bool(p.get("focused")), "kind": kind, "status": st,
                                      "title": p.get("terminal_title_stripped", ""), "cwd": p.get("cwd", "")})
    if not lines:
        eprint("desk: 无工位可列(机全不可达或零工位)")
    if not core.JSON_MODE:
        print("\n".join(lines))
    if dead:
        eprint(f"desk: 不可达机 {len(dead)} 台跳过({', '.join(dead)});单机详查:desk view <host>")
    emit_ok({"workspaces": json_rows})


def agents_main():
    g, verb, pos = parse(sys.argv[1:])
    setup("agents", g)
    handle_globals(g, manual("agents"))
    verb = verb or "view"
    if verb == "view":
        agents_view(pos[0] if pos else None)
    elif verb in ("workbenches", "ws"):
        # 工作台清点(用户令 2026-10-17):工作台 = 节点 home + ~/repos/* 各 git 仓(对 GitHub 项目)
        from .agents_ws_scan import scan
        scan(pos[0] if pos else None, g)
    elif verb == "yolo":
        # 四家 CLI yolo 检测与翻台(用户令 2026-10-17):裸/审计 = 全舰队屏面检测;
        # yolo <id> --yes = 冷翻(用户级配置 + /exit + fresh 起)
        from .agents_yolo import yolo_main
        yolo_main(pos, g)
    elif verb == "machines":
        print(f"{'MACHINE':<12} {'PANE':<8} REACHABLE")
        print(f"{'local':<12} {len(_agents_of(None)):<8} yes")
        for lab in _machine_labels():
            try:
                n = len(_agents_of(lab))
                print(f"{lab:<12} {n:<8} yes")
            except Exception:
                print(f"{lab:<12} {'?':<8} no")
    elif verb == "list":
        m = pos[0] if pos else None
        import json as _j
        print(_j.dumps(_agents_of(m or None), ensure_ascii=False))
    elif verb == "read":
        # 收件面(隐式):读格内容;目标在跑则内候到闲/完成或超时;状态随出
        if not pos:
            die("usage", "read <id> [--lines N] [--timeout S]", rc=2)
        m, pane = resolve(pos[0])
        lines = _val(pos, "--lines", "20")
        try:
            secs = int(_val(pos, "--timeout", "90"))
        except ValueError:
            die("usage", "--timeout 须为秒数", rc=2)
        deadline = time.time() + secs
        route = None if m in ("", "local") else m
        while True:
            st = target_status(m, pane)
            r = herdr_run(route, "agent", "read", pane,
                          "--source", "recent-unwrapped", "--lines", lines, timeout=max(secs, 5) + 10)
            content = (r.stdout or "").strip()
            if st != "working" or time.time() >= deadline:
                if content:
                    print(content)
                    emit_ok({"status": "timeout-working" if st == "working" else st, "target": f"{m}:{pane}"})
                else:
                    die("engine_fail", f"read {m}:{pane} 无内容且状态 {st};目标可能清屏或引擎忙,--timeout 加长重试", rc=1)
                break
            time.sleep(5)
    elif verb == "to":
        if len(pos) < 2:
            die("usage", f"{verb} <id> <文本> [--force]", rc=2)
        m, pane = resolve(pos[0])
        text = " ".join(pos[1:])
        blocked = gate(m, pane)
        if blocked:
            from .domains import s5_append
            try:
                s5_append(f"room/deferred/{pane}", f"{host_label()}|mode=deferred|domain=agents|「{text[:80]}」待投递(--force 重发)")
                eprint(f"agents: 目标存在操作对话框,已拒投并代记 room/deferred/{pane};下一步:--force 跳过门控重发")
            except Exception:
                eprint(f"agents: 目标存在操作对话框,已拒投;下一步:--force 重发,或以 streams append 记流")
            emit_ok({"status": "deferred", "target": f"{m}:{pane}"})
            sys.exit(1)
        from .msg import MsgEnvelope
        from .domains import caller_addr, _my_alias
        src = caller_addr()
        src_host, src_agent = (src.split(":", 1) + [""])[:2]
        dst_alias0 = next((a.get("name") for a in _agents_of(None if m in ("", "local") else m)
                           if a.get("pane_id") == pane), None)
        dst_c0 = (f"{host_label() if m in ('', 'local') else m}:{dst_alias0}" if dst_alias0 else pos[0])
        env = MsgEnvelope(domain="agents", src_host=src_host, src_pane=src_agent,
                          dst=dst_c0, body=text)
        # 双轨制(用户令 2026-10-15):from=机器:agent别名,取用行 = bare alias直答
        _alias = _my_alias()
        use = (f"agents to {_alias} reply" if _alias
               else (f"agents to {src_host}:{src_agent} reply" if src_agent
                     else f"agents view, locate the sender pane on {src_host}, then agents to <node:agent-alias> reply"))
        st = deliver_prompt(m, pane, env.render(use))
        if st == "delivered":
            # dm 双写(2026-10-23 用户令:agents 绑定 streams,回信事件道):
            # 出站信封镜像进 dm 对流,对端回信同样镜像,wait/inbox 即事件面
            # 3.9.1 修:pair 走 canonical 目标(机:别名,格回退),同一收方不同写法同一条流,不再劈叉
            try:
                from .domains import s5_append
                me_host = src_host if src_host != "local" else host_label()
                me_c = f"{me_host}:{_alias}" if _alias else me_host
                pair = sorted([me_c, dst_c0])
                one_line = f"{env.fieldline()} | {env.body} | {use}"
                s5_append(f"dm/{pair[0]}/{pair[1]}", one_line)
            except Exception:
                pass  # 镜像失败不拦投递主面(wait 面自然缺此条,主投递不受损)
            print(f"agents: 已投递,目标已开始处理(target={m}:{pane})")
            emit_ok({"status": st, "target": f"{m}:{pane}"})
        else:
            # 3.9.1 修:engine_fail 定向诊断(远程机在册但别名不在该机 = 寻址错非引擎错)
            if st == "engine_fail" and m not in ("", "local"):
                ags = _agents_of(m)
                names = [a.get("name") or a.get("pane_id") for a in ags if a.get("name")]
                if names:
                    eprint(f"agents: {m} 在册但投递失败;该机命名格:{', '.join(names[:8])};核对 id 或 agents view {m}")
            else:
                eprint(f"agents: 投递状态 {st}(target={m}:{pane});下一步:检查目标与引擎后重试")
            emit_ok({"status": st, "target": f"{m}:{pane}"})
            sys.exit(1)
    elif verb in ("wait", "inbox"):
        # 事件驱动收件面(2026-10-23 用户令:文字回信走 streams 事件道):
        # wait = 阻塞等新入站信封(dm 流,引擎级轮询,agent 不再盲等);inbox = 非阻塞收件单
        if not pos:
            pos = []
        from .domains import s5_tail_streams, s5_tail, caller_addr, _my_alias
        me_addr = caller_addr()
        alias_c = _my_alias() or ""
        short = me_addr.split(":", 1)[1] if ":" in me_addr else me_addr
        me_host_c = host_label()
        forms = [f for f in {me_addr, alias_c, short, f"{me_host_c}:{alias_c}" if alias_c else ""} if f]
        fromf = _val(pos, "--from", "")
        streams = []
        for x in s5_tail_streams():
            n = x.get("name", "")
            if n and any(f and f in n for f in forms):
                streams.append(n)
        if not streams:
            if verb == "inbox":
                print("(dm 流无入站;收到 agents to 回信后此处即现)")
                emit_ok({"status": "empty", "streams": []})
            else:
                emit_ok({"status": "timeout", "streams": []})
                sys.exit(1)
            return
        from .msg import parse_fieldline

        def _inbound(body: str) -> bool:
            fl = next((l for l in body.splitlines() if l.startswith("from=")), "")
            if not fl:
                return False  # 非信封条目(streams dm 裸文)不走事件面,streams view 直读
            d = parse_fieldline(fl)
            to, frm = d.get("to", ""), d.get("from", "")
            mine = to in forms or any(to.endswith(":" + f) for f in forms if f)
            if frm == me_addr or frm in forms:
                return False  # 自己的出站镜像
            if fromf and fromf not in frm:
                return False
            return mine

        cursors: dict[str, int] = {}
        for n in streams:
            es = s5_tail(n, 1)
            cursors[n] = es[-1]["seq_num"] if es else 0
        if verb == "inbox":
            shown = 0
            for n in streams:
                for e in s5_tail(n, 20):
                    if _inbound(e.get("body") or ""):
                        print(f"== {n} seq={e.get('seq_num')} ==")
                        print(e.get("body") or "")
                        shown += 1
            emit_ok({"status": "listed", "count": shown})
            return
        try:
            secs = int(_val(pos, "--timeout", "300"))
        except ValueError:
            die("usage", "--timeout 须为秒数", rc=2)
        deadline = time.time() + secs
        while time.time() < deadline:
            for n in streams:
                es = s5_tail(n, 50, cursors.get(n, 0))
                for e in es:
                    if e.get("seq_num", 0) <= cursors.get(n, 0):
                        continue
                    cursors[n] = e.get("seq_num", 0)
                    if _inbound(e.get("body") or ""):
                        print(f"== {n} seq={e.get('seq_num')} ==")
                        print(e.get("body") or "")
                        emit_ok({"status": "received", "stream": n, "seq": e.get("seq_num")})
                        return
            time.sleep(2)
        emit_ok({"status": "timeout", "streams": streams})
        sys.exit(1)
    elif verb == "start":
        # agents start <名> --kind <类> [--pane host:pane] [--cwd DIR] [--machine 机]
        if not pos:
            die("usage", "start <名> --kind <类> [--pane 格] [--cwd DIR] [--machine 机]", rc=2)
        name = pos[0]
        import re as _re
        # 命名标准定稿(2026-10-15 用户裁六项):start 拒新非标形(标准形禁下划线,
        # 从右解析恒成立);起名时全舰队唯一扫(herdr 只保本机 live 唯一)
        if not _re.match(r"^[a-z][a-z0-9-]{0,30}-(claude|codex|grok|kimi|pi)(-[0-9]{1,2})?$", name):
            die("usage", f"起名「{name}」非标准形(标准 = 台标签-agent类型-编号,字母开头禁下划线,编号 1-99 出生序号)",
                "存量名兼容在册;新起照标准形(如 myws-claude-1)", rc=2)
        taken = {(a.get("name") or "") for a in _agents_of(None)}
        for lab in _machine_labels():
            taken |= {(a.get("name") or "") for a in _agents_of(lab, timeout=8)}
        if name in taken:
            die("usage", f"起名「{name}」与在役 agent 撞名(全舰队唯一扫)",
                "agents view 查全局格表换名", rc=2)
        kind = _val(pos, "--kind", "claude")
        pane = _val(pos, "--pane", "")
        m = _val(pos, "--machine", "")
        # 消费掉旗标与其值,余位 = AGENT_ARGS 透传(经 -- 逃生口进的正文也算)
        consumed = set()
        for i, p in enumerate(pos):
            if p in ("--kind", "--pane", "--machine", "--cwd"):
                consumed.add(i)
                if i + 1 < len(pos):
                    consumed.add(i + 1)
        agent_args = [p for i, p in enumerate(pos) if i not in consumed]
        if pane and ":" in pane:
            pre = pane.split(":", 1)[0]
            if pre == "local" or pre in _machine_labels():
                if pre != "local":
                    m = m or pre
                pane = pane.split(":", 1)[1]
        args = ["agent", "start", name, "--kind", kind]
        if pane:
            args += ["--pane", pane]
        if agent_args:
            args += ["--"] + agent_args
        r = herdr_run(None if m in ("", "local") else m, *args)
        print(r.stdout or r.stderr)
        sys.exit(r.returncode)
    elif verb == "ws":
        # agents ws <label> [--cwd DIR] [--machine 机] | ws list [机] | ws close <台id> [机]
        sub = pos[0] if pos else "list"
        rest = pos[1:]
        if sub == "list":
            m = rest[0] if rest else ""
            if m and m not in _machine_labels() and m != "local":
                eprint(f"agents: 「{m}」不在册,本机列举(--machine 语义收主机标签;desk ws list 无参 = 本机)")
            r = herdr_run(None if m in ("", "local") else m, "workspace", "list")
            print(r.stdout or r.stderr)
        elif sub == "close":
            if not rest:
                die("usage", "ws close <台id> [机]", rc=2)
            m = rest[1] if len(rest) > 1 else ""
            r = herdr_run(None if m in ("", "local") else m, "workspace", "close", rest[0])
            print(r.stdout or r.stderr)
        else:
            cwd = _val(rest, "--cwd", "")
            m = _val(rest, "--machine", "")
            args = ["workspace", "create", "--label", sub]
            if cwd:
                args += ["--cwd", cwd]
            r = herdr_run(None if m in ("", "local") else m, *args)
            pid = _json_field(r.stdout, "root_pane", "pane_id")
            print(r.stdout or r.stderr)
            if pid:
                eprint(f"agents: 台建 {sub}(root={pid})")
    elif verb == "shell":
        # agents shell <机> <仓绝对路径或仓名>:开该机该仓工作台 shell,回 root pane id
        if len(pos) < 2:
            die("usage", "shell <机> <仓库路径>", rc=2)
        m, repo = pos[0], pos[1]
        label = repo.rstrip("/").split("/")[-1]
        r = herdr_run(m, "workspace", "create", "--label", label, "--cwd", repo)
        pid = _json_field(r.stdout, "root_pane", "pane_id")
        print(pid or (r.stdout or r.stderr))
        sys.exit(0 if pid else 1)
    elif verb == "dev":
        # agents dev <机> <仓库> [--kind 类]:开台并起 agent(名 = 仓名)
        if len(pos) < 2:
            die("usage", "dev <机> <仓库路径> [--kind 类]", rc=2)
        m, repo = pos[0], pos[1]
        kind = _val(pos, "--kind", "claude")
        label = repo.rstrip("/").split("/")[-1]
        r = herdr_run(m, "workspace", "create", "--label", label, "--cwd", repo)
        pid = _json_field(r.stdout, "root_pane", "pane_id")
        if not pid:
            eprint(f"agents dev: 台建失败({m} {repo}):{(r.stderr or r.stdout).strip()[:120]}")
            sys.exit(1)
        r2 = herdr_run(m, "agent", "start", label, "--kind", kind, "--pane", pid)
        print(pid)
        eprint((r2.stdout or r2.stderr).strip()[:200])
        # 启动后阻塞检测(用户令:不是启动就不管 TUI 阻不阻塞)
        hit = _blocked_after_start(m, pid, kind, wait_s=30)
        if hit:
            for line in _dismiss_block_hint(hit):
                eprint(line)
            from .core import emit_ok as _eo
            import sys as _sys
            _eo({"status": "blocked", "pane": pid, "kind": kind, "marker": hit["marker"],
                 "cta": "人工放行(↓+Enter)或 --force 投递"})
            _sys.exit(1)
    elif verb == "split":
        # agents split <id> [--direction right|down]
        if not pos:
            die("usage", "split <id> [--direction right|down]", rc=2)
        m, pane = resolve(pos[0])
        d = _val(pos, "--direction", "right")
        r = herdr_run(None if m in ("", "local") else m, "pane", "split", pane, "--direction", d)
        print(r.stdout or r.stderr)
        sys.exit(r.returncode)
    elif verb == "tab":
        # agents tab list [机] | create <机> [--label 名] | close <机:tabid>
        sub = pos[0] if pos else "list"
        rest = pos[1:]
        if sub == "list":
            m = rest[0] if rest else ""
            if m and m not in _machine_labels() and m != "local":
                eprint(f"agents: 「{m}」不在册,本机列举(--machine 语义收主机标签;desk ws list 无参 = 本机)")
            r = herdr_run(None if m in ("", "local") else m, "tab", "list")
            print(r.stdout or r.stderr)
        elif sub == "create":
            if not rest:
                die("usage", "tab create <机> [--label 名]", rc=2)
            m = rest[0]
            args = ["tab", "create"] + rest[1:]
            if "--workspace" not in rest[1:]:
                args += ["--workspace", m] if False else []
            r = herdr_run(m, *args)
            print(r.stdout or r.stderr)
        elif sub == "close":
            if not rest:
                die("usage", "tab close <机:tabid>", rc=2)
            m, tid = resolve_tab(rest[0])
            r = herdr_run(m, "tab", "close", tid)
            print(r.stdout or r.stderr)
        else:
            die("usage", "tab list|create|close", rc=2)
    elif verb == "zoom":
        if not pos:
            die("usage", "zoom <id>", rc=2)
        m, pane = resolve(pos[0])
        r = herdr_run(None if m in ("", "local") else m, "pane", "zoom", pane)
        print(r.stdout or r.stderr)
        sys.exit(r.returncode)
    elif verb == "run":
        # agents run <id> <命令...>(格内跑命令;herdr pane run 原语壳)
        if len(pos) < 2:
            die("usage", "run <id> <command...>(run a command in a pane)", rc=2)
        target = pos[0]
        m, pane = (target.split(":", 1) + [""])[:2] if ":" in target else ("local", target)
        herdr_run(None if m in ("", "local") else m, "pane", "run", pane, *pos[1:])
        emit_ok({"status": "delivered", "target": target, "command": " ".join(pos[1:])})
    elif verb == "keys":
        # agents keys <id> <键>...:send-keys 串(本机优先;跨机机: 形直发)
        if len(pos) < 2:
            die("usage", "keys <id> <键>...", rc=2)
        target = pos[0]
        if ":" in target:
            m, pane = target.split(":", 1)[0], target.split(":", 1)[1]
        else:
            hit = core._find_by_name("", target)
            m, pane = (hit or ("local", target))
        for k in pos[1:]:
            herdr_run(None if m in ("", "local") else m, "agent", "send-keys", pane, k)
        eprint(f"agents: 已发键 {' '.join(pos[1:])} → {m}:{pane}")
    elif verb == "mode":
        # agents mode <dnd|away|online> [until](本机 presence 声明,shares 键覆盖写)
        if not pos or pos[0] not in ("dnd", "away", "online"):
            die("usage", "mode <dnd|away|online> [until=ISO时刻]", rc=2)
        from .domains import caller_addr
        import tempfile
        modearg = pos[0]
        until = _val(pos, "until", pos[1] if len(pos) > 1 else "")
        from .domains import caller_pane
        pane = caller_pane()
        key = f"share/presence/{host_label()}/{pane}"
        tmp = os.path.join(tempfile.gettempdir(), f"prim-presence-{pane.replace(':', '_')}")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(f"mode={modearg}\nuntil={until}\n")
        r = subprocess_run(core.s5_cmd() + ["put", core.wsl_path(tmp), key])
        try:
            os.remove(tmp)
        except OSError:
            pass
        if r.returncode == 0:
            print(f"agents: presence={modearg}{' until=' + until if until else ''}(key={key})")
        else:
            die("engine_fail", f"presence 写败:{(r.stderr or '').strip()[:100]}", rc=1)
    elif verb == "reload":
        # agents reload <id>:无痛刷新(退出 agent → 同格同 session 重进 → 技能/插件重载)
        # 原语自修正:名字自动按 herdr 规则矫正;重进失败自动回滚试裸形
        if not pos:
            die("usage", "reload <id>(同会话重进,重载技能与插件;重载铁律:旧进程等于旧技能)", rc=2)
        m, pane = resolve(pos[0])
        route = None if m in ("", "local") else m
        ag = next((a for a in _agents_of(route) if a.get("pane_id") == pane), None)
        if not ag:
            die("not_found", f"{m}:{pane} 无 agent 在跑", [{"command": "agents view", "description": "查全局格表"}])
        # 可翻门(2026-10-13 idle 门,2026-10-15 修):idle/done 皆可翻(done = 活完等单,
        # 与 idle 同为安全态;互相翻台批实证 done 被拒是误伤);working/blocked 拒,--force 过
        st = ag.get("agent_status") or "unknown"
        if st not in ("idle", "done") and not core.FORCE:
            die("deferred",
                f"reload 目标状态 {st}(非 idle),翻台拒绝;下一步:候其 idle 再 reload,或 --force 强翻",
                [{"command": "agents read " + pos[0], "description": "看目标在做什么"}], rc=1)
        kind = ag.get("agent") or "claude"
        # 台标签真源 = herdr workspace label(用户令 2026-10-13:herdr api 可自定义);退化 cwd 仓名
        label = ""
        for w in herdr_json(route, "workspace", "list"):
            if isinstance(w, dict) and w.get("workspace_id") == ag.get("workspace_id"):
                label = w.get("label") or ""
                break
        if not label:
            label = (ag.get("cwd") or "").replace("\\", "/").rstrip("/").split("/")[-1]
        import re as _re2
        label = _re2.sub(r"[^a-z0-9-]", "-", (label or "ws").lower())[:20] or "ws"
        # 编号 = 出生序号(命名标准 2026-10-15 裁 2):该台该类型现役最大号 + 1,不复用
        _pref = f"{label}-{kind}-"
        _seqs = [int(_m.group(1)) for a0 in _agents_of(None)
                 if (a0.get("name") or "").startswith(_pref)
                 and (_m := _re2.match(rf"^{_re2.escape(_pref)}([0-9]{{1,2}})$", a0["name"]))]
        _seq = (max(_seqs) + 1) if _seqs else 1
        raw = ag.get("name") or f"{_pref}{_seq}"
        # 名字保真(用户令 + evo 批②):存量名(含非标形如 hst_rs)一律保名重用,防身份断裂;
        # 仅无名字才派生标准形;非法字符名才自修正并信封披露 old-name
        import re as _re2
        if raw and _re2.match(r"^[a-z0-9_][a-z0-9_-]{0,31}$", raw):
            name = raw
        elif raw:
            name = _re2.sub(r"[^a-z0-9_-]", "-", raw.lower())[:32].strip("-") or f"{label}-{kind}-1"
        else:
            name = f"{label}-{kind}-1"
        if name != raw:
            eprint(f"agents: 名字「{raw}」不合 herdr 规则,自修正为「{name}」(信封披露 old-name={raw})")
        # 1) 干净退场;CC 带任务格 /exit 弹三选一(Exit and stop tasks),扫屏选 1 + enter
        herdr_run(route, "agent", "prompt", pane, "/exit", timeout=30)
        for _ in range(8):  # 对话框扫描窗 16s
            time.sleep(2)
            rr = herdr_run(route, "agent", "read", pane, "--source", "visible", "--lines", "12", timeout=10)
            if "Exit and stop tasks" in (rr.stdout or ""):
                herdr_run(route, "agent", "send-keys", pane, "1", timeout=10)
                time.sleep(1)
                herdr_run(route, "agent", "send-keys", pane, "enter", timeout=10)
                break
        exited = False
        for _ in range(30):  # 肥会话(数十万 token)/exit 落盘慢,窗 30s 放宽 60s
            time.sleep(2)
            if not any(a.get("pane_id") == pane and a.get("agent") for a in _agents_of(route)):
                exited = True
                break
        if not exited:
            die("engine_fail", f"{m}:{pane} 退出超时(60s);下一步:人工查屏(该家 TUI 退出形可能非 /exit)", rc=1)
        # 2) 同 session 重进(四家 resume 形在册);失败自回滚裸形再试一次
        # claude 形根修(2026-10-14 实证定谳):/exit 后 daemon 把会话留成后台
        # (--fork-session --resume 进程在册),--continue 撞「最近会话在后台跑」即拒;
        # 正形 = --resume 出会话选择画面,补一发 Enter 接最近会话(用户裁定 2026-10-14)
        rargs = {"claude": ["--resume"], "codex": ["resume", "--last"],
                 "grok": ["--continue"], "kimi": ["--continue"]}.get(kind)
        if not rargs:
            die("usage", f"kind「{kind}」无 resume 形在册;下一步:人工重进后 agents start 补名", rc=2)
        post_keys = ["enter"] if kind == "claude" else []  # claude: 选择画面回车接最近

        def _pane_started(wait_s: int = 20) -> bool:
            # claude 启动面(插件/MCP 加载)常超 herdr 探测窗;轮询等注册而非单探
            for _ in range(max(1, wait_s // 2)):
                if any(a.get("pane_id") == pane and a.get("agent") for a in _agents_of(route)):
                    return True
                time.sleep(2)
            return False

        def _start(*extra: str, timeout: int = 150, startup_ms: int = 120000) -> subprocess.CompletedProcess:
            # herdr 探测窗缺省 30s;claude 插件/MCP 启动面常超窗 → 提到 120s(批147 根因)
            return herdr_run(route, "agent", "start", name, "--kind", kind, "--pane", pane,
                             "--timeout", str(startup_ms),
                             *(["--", *extra] if extra else []), timeout=timeout)

        r = _start(*rargs)
        # 判定以 herdr 回执 JSON 为准(其退出码恒 0,timeout 也走 stdout error 形,rc 不可信)
        ok = "agent_started" in (r.stdout or "")
        fresh = False
        if not ok and _pane_started():
            # herdr startup 探测窗超时/瞬态失败,但格上 agent 已在起;不回滚
            ok = True
            eprint("agents: start 回执超时但格上 agent 已在起(恢复慢于探测窗,非失败;不回滚)")
        elif not ok:
            eprint(f"agents: resume 形重进失败,首发回执:{(r.stderr or r.stdout or '').strip()[:200]}")
            eprint("agents: 自回滚裸形(新会话)再试")
            r = _start()
            fresh = True
            ok = ("agent_started" in (r.stdout or "")) or _pane_started()
        # claude 形:agent 就绪即在选择画面,补 Enter 击键接最近会话(agent send-keys 面)
        if ok and not fresh and post_keys:
            time.sleep(3)
            for k in post_keys:
                herdr_run(route, "agent", "send-keys", pane, k, timeout=15)
        print(r.stdout or r.stderr)
        emit_ok({"status": "delivered" if ok else "engine_fail",
                 "target": f"{m}:{pane}", "kind": kind, "name": name,
                 "resume": (" ".join(rargs) if not fresh else "fresh-session") if ok else "none"})
        if not ok:
            sys.exit(1)
    elif verb == "close":
        # agents close <id>:关格,全 herdr 原生零击杀
        # 序 = agent 优雅退(/exit 持久化)→ 裸格 pane run "exit"(原子送文本+回车)→ 格随 shell 退出自消
        # (evo 批③:写盘中丢稿面已消——本形恒先 /exit 优雅退,shell exit 只是末步;--force 不再需要杀语义)
        if not pos:
            die("usage", "close <id>(agent 优雅退场后 shell exit,格自消)", rc=2)
        m, pane = resolve(pos[0])
        route = None if m in ("", "local") else m
        ag = next((a for a in _agents_of(route) if a.get("pane_id") == pane), None)
        # 1) agent 在跑 → 优雅退场(/exit 会话持久化,--continue 可接回)
        if ag and ag.get("agent"):
            herdr_run(route, "agent", "prompt", pane, "/exit", timeout=30)
            for _ in range(15):
                time.sleep(2)
                if not any(a.get("pane_id") == pane and a.get("agent") for a in _agents_of(route)):
                    break
        # 2) 裸格输入 exit(pane run = 原子文本+回车),shell 退出格自消
        r = herdr_run(route, "pane", "run", pane, "exit", timeout=15)
        if r.returncode != 0:
            # 兜底:末格尝试 workspace close(herdr 原生)
            ws_id = (ag or {}).get("workspace_id") or ""
            if not ws_id:
                rg = herdr_run(route, "pane", "get", "--pane", pane)
                ws_id = _json_field(rg.stdout, "pane", "workspace_id")
            if ws_id:
                herdr_run(route, "workspace", "close", ws_id)
            else:
                die("engine_fail", f"close {m}:{pane} 面上 exit 与台收皆败:{(r.stderr or r.stdout).strip()[:80]};下一步:agents view 人工核", rc=1)
        for _ in range(10):
            time.sleep(1)
            if pane not in {a.get("pane_id") for a in _agents_of(route)}:
                print(f"agents: 已关 {m}:{pane}(shell exit,格自消)")
                emit_ok({"status": "delivered", "target": f"{m}:{pane}", "method": "pane-run-exit"})
                return
        die("engine_fail", f"close {m}:{pane} 10s 内格未消;下一步:agents view 复核", rc=1)
    elif verb == "wt":
        # agents wt [机] [--title 名]:总台本窗开 tab 显示该机 herdr 视图
        # (wt 是显示面:本窗 = -w 0;在册机走 ssh -t;win 专属动词)
        if os.name != "nt":
            die("usage", "wt 动词为 Windows Terminal 专属;linux/macos 用 herdr 本体", rc=2)
        target = pos[0] if pos else "local"
        title = _val(pos, "--title", "")
        if target in ("", "local"):
            args = ["wt", "-w", "0", "new-tab", "--title", title or "herdr", "herdr"]
        elif target in _machine_labels():
            args = ["wt", "-w", "0", "new-tab", "--title", title or target, "ssh", "-t", target, "herdr"]
        else:
            die("usage", "wt [机] [--title 名](本窗开 tab 显示该机 herdr;机表 = agents machines)", rc=2)
        r = subprocess_run(args)
        ok = r.returncode == 0
        print(f"agents: wt tab 已开({target},本窗)" if ok else f"agents: wt 开败:{(r.stderr or r.stdout).strip()[:80]}")
        emit_ok({"status": "delivered" if ok else "engine_fail", "view": target})
        if not ok:
            sys.exit(1)
    elif verb == "trust":
        # 信任屏放行:全机 blocked/unknown 格扫屏按键(判标库 shell v2.8 同源)
        _agents_trust(None)
    elif verb == "sync":
        # agents sync [机]:mesh 补注册(每端跑一次,把本机 server 注册进对端机册)
        m = pos[0] if pos else ""
        r = herdr_run(None if m in ("", "local") else m, "machine", "list", "--json")
        print(r.stdout or r.stderr)
        eprint("agents sync: 机册注册面 = 各端互注册;新端走 G011 第 8 步 machine add")
    else:
        # 透传(允许表 = herdr agent 子命令)
        if not pos:
            die("usage", f"未知动词「{verb}」;--llms 看手册", rc=2)
        m, pane = resolve(pos[0])
        r = herdr_run(None if m in ("", "local") else m, "agent", verb, pane, *pos[1:])
        print(r.stdout or r.stderr)
        sys.exit(r.returncode)

# ---------- 其余六命令(实现见 domains.py 与 ctx.py) ----------

def _load(cmd: str):
    """惰性取域入口:agents 在本文件,五域在 domains,ctxs/mcps 各自模块。"""
    if cmd == "ctxs":
        from . import ctx as _ctx
        return _ctx.ctxs_main
    if cmd == "machines":
        from . import nodes as _nodes
        return _nodes.machines_main
    if cmd == "mcps":
        from . import mcps as _mcps
        return _mcps.mcps_main
    from . import domains
    return getattr(domains, f"{cmd}_main")

def _guard(fn):
    """顶层 Ctrl+C 净化:单行退出码 130,不出 traceback(孙进程收割在 herdr_run)。"""
    import functools
    @functools.wraps(fn)
    def _w(*a, **kw):
        try:
            fn(*a, **kw)
        except KeyboardInterrupt:
            eprint(f"{core.CMD_NAME}: 已中断(Ctrl+C)")
            sys.exit(130)
    return _w

agents_main = _guard(agents_main)
shares_main = _guard(_load("shares"))
streams_main = _guard(_load("streams"))
tasks_main = _guard(_load("tasks"))
pipes_main = _guard(_load("pipes"))
ports_main = _guard(_load("ports"))
ctxs_main = _guard(_load("ctxs"))
mcps_main = _guard(_load("mcps"))
machines_main = _guard(_load("machines"))

def desk_main():
    """desks 域(ADR-0007 拓扑面 + ADR-0008 复数对齐):工位(pane)/窗台(workspace)操作器。
    主名 desks(全家族复数形),desk 留单字别名(软切期);view = 拓扑真视图(窗台/tab/工位/焦点/活动);
    start/close/split/tab/zoom/ws/shell/dev/wt/yolo/trust 动词与 agents 同实现(软拆 alias 期)。"""
    if len(sys.argv) > 1 and sys.argv[1] in ("--llms", "--help", "-h"):
        print(f"desks@{_pkg_ver()} - 工位(pane)/窗台(workspace)操作器(拓扑面,ADR-0007+0008 复数对齐;消息面走 agents,机册走 machines;desk 为旧名单字别名)")
        print("术语:工位/窗格 = pane(p1,p1W);工作台/窗台 = workspace(w 编号,一个终端窗)")
        print("view [host](拓扑视图:窗台->tab->工位分组,▍ 焦点工位,活动列 = 标题;含非 agent 工位;裸调用同)")
        print("动词(与 agents 同实现,软拆 alias 期):")
        print("  start <名> --kind <类> [--pane 格] [--cwd DIR] [--machine 机];close <id>(优雅退)")
        print("  split <id> [--direction right|down];tab <list|create|close>;zoom <id>;wt [机] [--title 名]")
        print("  ws <label> [--cwd DIR] [--machine 机]|ws list [机]|ws close <台>;shell <机> <仓路径>;dev <机> <仓路径> [--kind 类]")
        print("  yolo [--audit]|yolo <id> [--yes](四家 CLI 检测/冷翻);trust(信任屏放行);reload <id>(重载技能)")
        print("id:裸名|机:名或格|local:格;示例:desks start hst-kimi-2 --kind kimi --cwd ~/repos/hst_rs;desks split evo-claude")
        print("alias 期:agents start/split/tab/... 同实现有效(1-2 大版本后收)")
        return
    argv = sys.argv[1:]
    g, verb, pos = parse(argv)
    setup("desk", g)
    # view 动词与裸调用 = desk 自有拓扑视图(与 agents view 消息面表分职);其余动词透传 agents 同实现
    if verb in (None, "view"):
        host = pos[0] if pos and not pos[0].startswith("-") else None
        return desk_view(host)
    return agents_main()

desk_main = _guard(desk_main)
