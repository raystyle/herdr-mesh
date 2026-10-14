"""prim CLI - 六原语命令入口(v3 python 形)

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

def manual(cmd: str) -> str:
    m = {
        "agents": f"""agents@v3 - 消息域:全局 pane 操作器(隐式路由,任何端点可用)
文法:agents [全局旗标] <动词> [动词旗标] [位置参数];裸调用 = view
全局旗标:--help -h --llms --json --force(投递)
动词:view [机];machines;list [机];read <id> [--lines N] [--timeout S];keys <id> <键>;
  to <id> <文本> [--force];prompt = to 别名;
  mode <dnd|away|online> [until](presence 走 shares 键);
  start <名> --kind <类> [--pane 格] [--cwd DIR] [--machine 机];
  ws <label> [--cwd DIR] [--machine 机]|ws list [机]|ws close <台> [机];
  shell <机> <仓路径>(开台 shell 回 root 格);dev <机> <仓路径> [--kind 类](开台+起 agent);
  split <id> [--direction right|down];tab <list [机]|create <机>|close <机:tab>>;
  zoom <id>;close <id>(关格零击杀:agent /exit 优雅退后 shell exit,格自消);
  wt [机|wsl] [--title 名](win 专属:本窗开 tab 显该机 herdr 视图);
  trust(信任屏放行);sync(机册面);reload <id>(同格同 session 重进,重载技能与插件)
id:裸名(全局)|机:名或格|local:格;裸 pane id 非法
示例:
  agents view
  agents read workbench-claude-1 --lines 20
  agents to workbench-grok-1 "评审请求已递" --json
  agents dev host-b ~/repos/app --kind grok""",
        "shares": f"""shares@v3 - 文件域:S3 中转(引擎 s5;内容哈希键)
动词:view;put <文件>;get <键> [--output 名];to <id> <文件> [--force](=上架+模板知会)
示例:
  shares put report.md
  shares to workbench-claude-1 report.md --json""",
        "streams": f"""streams@v3 - 流域:S2 持久流(引擎 s5;流即房间)
动词:view [流名] [--from <seq>|--resume] [-n N];append <流> <消息>;to <id> <流> <消息> [--force]
示例:
  streams view fleet --from 0
  streams view fleet --from 23 -n 2
  streams to workbench-grok-1 fleet "回执:批 X 完成\"""",
        "tasks": f"""tasks@v3 - 持久任务域:hst task 全局遥控(引擎 hst)
动词:view [机](实时任务面:fleet 状态总览加本机各仓 hst task show 直读;远机任务经 agents read <id> 看屏);
  set <id> <文本>;to <id> <文本> [--force](=set+事件+知会)
示例:
  tasks view
  tasks to s5_rs "评审收束后发版\"""",
        "pipes": f"""pipes@v3 - 管道域:tailcat 实时(本机收对方发)
动词:view [机];open [--keep];close <addr|pid>;to <id> [--force](=open+模板知会)
示例:
  pipes view host-b
  pipes to workbench-grok-1""",
        "ctx": """ctx@v3 - 对话历史域:agent 请求全链检索(引擎 ClickHouse gw_logs;与 agents read 分工:read=实时屏,ctx=历史档案)
动词:view [agent] [--limit N](最近请求头行:时间/模型/token/耗时/request_id);
  show <request_id>(单请求头行加正文块,每块截 4000 字);
  search <关键词> [--limit N](跨请求全文)
窗口:head 365 天,gwlog 正文 180 天
示例:
  ctx view
  ctx view workbench-claude-1 --limit 5
  ctx show 0192a0f0-xxxx
  ctx search "panic\"""",
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

def agents_view(machine: str | None):
    rows = _agents_of(machine or None)
    if not machine:
        rows = [("local", a) for a in rows]
        dead = []
        for lab in _machine_labels():
            got = _agents_of(lab)
            if not got:
                dead.append(lab)
                continue
            rows += [(lab, a) for a in got]
        print(f"{'HOST':<12} {'NAME':<12} {'PANE':<8} {'STATUS':<8} {'KIND':<7} CWD")
        for host, a in rows:
            print(f"{host:<12} {(a.get('name') or '-'):<12} {a.get('pane_id',''):<8} {a.get('agent_status',''):<8} {(a.get('agent') or '-'):<7} {a.get('cwd','')}")
        if dead:
            eprint(f"agents: 不可达机 {len(dead)} 台跳过({', '.join(dead)});单机详查:agents view <机>")
    else:
        for a in rows:
            print(f"{a.get('pane_id',''):<8} {(a.get('name') or '-'):<12} {a.get('agent_status',''):<8} {a.get('cwd','')}")

def agents_main():
    g, verb, pos = parse(sys.argv[1:])
    setup("agents", g)
    handle_globals(g, manual("agents"))
    verb = verb or "view"
    if verb == "view":
        agents_view(pos[0] if pos else None)
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
    elif verb in ("to", "prompt"):
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
        from .domains import caller_addr
        src = caller_addr()
        src_host, src_pane = (src.split(":", 1) + [""])[:2]
        env = MsgEnvelope(domain="agents", src_host=src_host, src_pane=src_pane,
                          dst=pos[0], body=text)
        use = (f"agents to {src_host}:{src_pane} <回复>" if src_pane
               else f"agents view(定位 {src_host} 上发话格后 agents to <机:格> <回复>)")
        st = deliver_prompt(m, pane, env.render(use))
        if st == "delivered":
            print(f"agents: 已投递,目标已开始处理(target={m}:{pane})")
            emit_ok({"status": st, "target": f"{m}:{pane}"})
        else:
            eprint(f"agents: 投递状态 {st}(target={m}:{pane});下一步:检查目标与引擎后重试")
            emit_ok({"status": st, "target": f"{m}:{pane}"})
            sys.exit(1)
    elif verb == "start":
        # agents start <名> --kind <类> [--pane 机:格] [--cwd DIR] [--machine 机]
        if not pos:
            die("usage", "start <名> --kind <类> [--pane 格] [--cwd DIR] [--machine 机]", rc=2)
        name = pos[0]
        import re as _re
        # 命名标准(用户令 2026-10-13):工作台标签-agent类型-编号(如 workbench-claude-1);存量名兼容,非标准形 stderr 提示不拦截
        if not _re.match(r"^[a-z0-9_][a-z0-9_-]*-(claude|codex|grok|kimi|pi)(-[0-9]+)?$", name):
            eprint(f"agents: 起名「{name}」非标准形(标准 = 台标签-agent类型-编号,如 workbench-claude-1);存量名兼容,新起建议标准形")
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
        addr = caller_addr()
        pane = addr.split(":", 1)[1] if ":" in addr else "unknown"
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
        # idle 门(用户令 2026-10-13:翻台只针对 idle):非 idle 拒,--force 过
        st = ag.get("agent_status") or "unknown"
        if st not in ("idle",) and not core.FORCE:
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
        label = _re2.sub(r"[^a-z0-9_-]", "-", (label or "ws").lower())[:20] or "ws"
        raw = ag.get("name") or f"{label}-{kind}-1"
        # 名字保真(用户令 + evo 批②):存量名(含非标形)一律保名重用,防身份断裂;
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
        # 1) 干净退场(claude 族 /exit 实证;他家先试 /exit,未退如实报)
        herdr_run(route, "agent", "prompt", pane, "/exit", timeout=30)
        exited = False
        for _ in range(15):
            time.sleep(2)
            if not any(a.get("pane_id") == pane and a.get("agent") for a in _agents_of(route)):
                exited = True
                break
        if not exited:
            die("engine_fail", f"{m}:{pane} 退出超时(30s);下一步:人工查屏(该家 TUI 退出形可能非 /exit)", rc=1)
        # 2) 同 session 重进(四家 resume 形在册);失败自回滚裸形再试一次
        rargs = {"claude": ["--continue"], "codex": ["resume", "--last"],
                 "grok": ["--continue"], "kimi": ["--continue"]}.get(kind)
        if not rargs:
            die("usage", f"kind「{kind}」无 resume 形在册;下一步:人工重进后 agents start 补名", rc=2)
        r = herdr_run(route, "agent", "start", name, "--kind", kind, "--pane", pane,
                      "--", *rargs, timeout=90)
        ok = "agent_started" in (r.stdout or "")
        if not ok:
            eprint("agents: resume 形重进失败,自回滚裸形(新会话)再试")
            r = herdr_run(route, "agent", "start", name, "--kind", kind, "--pane", pane, timeout=90)
            ok = "agent_started" in (r.stdout or "")
        print(r.stdout or r.stderr)
        emit_ok({"status": "delivered" if ok else "engine_fail",
                 "target": f"{m}:{pane}", "kind": kind, "name": name,
                 "resume": " ".join(rargs) if ok else "fresh-session"})
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
        # agents wt [机|wsl] [--title 名]:总台本窗开 tab 显示该机 herdr 视图
        # (wt 是显示面:本窗 = -w 0;wsl 走 wsl.exe 绝对路径道,在册机走 ssh -t;win 专属动词)
        if os.name != "nt":
            die("usage", "wt 动词为 Windows Terminal 专属;linux/macos 用 herdr 本体", rc=2)
        target = pos[0] if pos else "local"
        title = _val(pos, "--title", "")
        if target in ("wsl", "ohmywsl"):
            args = ["wt", "-w", "0", "new-tab", "--title", title or "wsl-herdr",
                    "wsl.exe", "-d", "ohmywsl", "--cd", "/home/ray", "--", "/home/ray/.local/bin/herdr"]
        elif target in ("", "local"):
            args = ["wt", "-w", "0", "new-tab", "--title", title or "herdr", "herdr"]
        elif target in _machine_labels():
            args = ["wt", "-w", "0", "new-tab", "--title", title or target, "ssh", "-t", target, "herdr"]
        else:
            die("usage", "wt [机|wsl] [--title 名](本窗开 tab 显示该机 herdr;机表 = agents machines)", rc=2)
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

# ---------- 其余五命令(实现见 domains.py 与 ctx.py) ----------

def _load(cmd: str):
    """惰性取域入口:agents 在本文件,四域在 domains,ctx 在 ctx。"""
    if cmd == "ctx":
        from . import ctx as _ctx
        return _ctx.ctx_main
    from . import domains
    return getattr(domains, f"{cmd}_main")

shares_main = _load("shares")
streams_main = _load("streams")
tasks_main = _load("tasks")
pipes_main = _load("pipes")
ctx_main = _load("ctx")
