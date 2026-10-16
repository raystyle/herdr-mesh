"""prim 五域实现(shares/streams/tasks/pipes/ports)——v3 python 形

各域骑其引擎(s5/hst/tailcat),DELIVER = 引擎操作 + 模板三行形 + agents to 投递(status 信封)
"""
from __future__ import annotations
from . import core
import hashlib
import json
import os
import subprocess
import sys
import time
from .core import (die, emit_ok, eprint, herdr_run,
                   resolve, host_label, deliver_prompt, gate, pane_cwd,
                   _agents_of, _machine_labels)

# ---------- s5 引擎封装(本机直跑;win 缺位走 wsl 代役,路径互转) ----------

def s5_run(*args: str, stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(core.s5_cmd() + list(args), capture_output=True, text=True,
                          input=stdin, timeout=60, encoding="utf-8", errors="replace")

def s5_append(stream: str, body: str) -> bool:
    r = s5_run("append", stream, stdin=body + "\n")
    return r.returncode == 0

def s5_tail(stream: str, n: int = 20, seq: int | None = None) -> list[dict]:
    args = ["tail", stream, "-n", str(n)]
    if seq is not None:
        args += ["--seq", str(seq)]
    r = s5_run(*args)
    out = []
    for line in (r.stdout or "").splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    # s5 语义:--seq 与 -n 互斥时 -n 被忽略(从 seq 续读到尾);本层自行限 N
    if seq is not None:
        return out[:n]
    return out

def s5_ls(prefix: str) -> list[dict]:
    r = s5_run("ls", prefix)
    out = []
    for line in (r.stdout or "").splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return out

# ---------- shares 域 ----------

def shares_put(filepath: str) -> str:
    if not os.path.isfile(filepath):
        die("usage", f"文件不存在:{filepath}", rc=2)
    h = hashlib.md5(open(filepath, "rb").read(65536)).hexdigest()[:10]
    base = os.path.basename(filepath)
    key = f"share/{host_label()}/{h}/{base}"
    r = s5_run("put", core.wsl_path(filepath), key)
    if r.returncode != 0:
        die("engine_fail", f"s5 put 失败:{(r.stderr or '').strip()[:120]}", rc=1)
    return key

def shares_main():
    from .cli import parse, setup, handle_globals, manual
    g, verb, pos = parse(sys.argv[1:])
    setup("shares", g)
    handle_globals(g, manual("shares"))
    verb = verb or "view"

    if verb == "view":
        print("-- share 资源(share/ 前缀):")
        for x in s5_ls("share/"):
            print(json.dumps(x, ensure_ascii=False))
    elif verb == "put":
        if not pos:
            die("usage", "put <文件>", rc=2)
        key = shares_put(pos[0])
        print(f"shares: 已上架 {key}")
        emit_ok({"status": "delivered", "key": key})
    elif verb == "get":
        if not pos:
            die("usage", "get <键> [--output 名]", rc=2)
        key = pos[0]
        out = None
        if "--output" in pos and pos.index("--output") + 1 < len(pos):
            out = pos[pos.index("--output") + 1]
        elif "-o" in pos and pos.index("-o") + 1 < len(pos):
            out = pos[pos.index("-o") + 1]
        if not out:
            out = key.split("/")[-1]
        r = s5_run("get", "-o", core.wsl_path(out), key)
        if r.returncode != 0:
            die("engine_fail", f"s5 get 失败:{(r.stderr or '').strip()[:120]}", rc=1)
        out = core.host_path(out)
        print(f"shares: 已取回 {out}")
        emit_ok({"status": "delivered", "key": key, "output": out})
    elif verb == "to":
        if len(pos) < 2:
            die("usage", "to <id> <文件> [--force]", rc=2)
        m, pane = resolve(pos[0])
        filepath = pos[1]
        blocked = gate(m, pane)
        key = shares_put(filepath)
        if blocked:
            # 先上架再代记(研究裁定:文件已在,人可取)
            s5_append(f"room/deferred/{pane}", f"{host_label()}|mode=deferred|domain=shares|文件 {key} 待达(--force 重发)")
            eprint(f"shares: 目标存在操作对话框,已拒投;文件已上架 {key};已代记 room/deferred/{pane}")
            emit_ok({"status": "deferred", "target": f"{m}:{pane}", "key": key})
            sys.exit(1)
        base = os.path.basename(filepath)
        src = caller_addr()
        src_host, src_pane = (src.split(":", 1) + [""])[:2]
        from .msg import MsgEnvelope
        env = MsgEnvelope(domain="shares", src_host=src_host, src_pane=src_pane,
                          dst=pos[0], key=key, name=base)
        # 双轨制(用户令 2026-10-15):消息收发面用 机:agent别名;窗格操作才用 机:格
        my = _my_alias() or f"{src_host}:{src_pane}"
        msg = env.render(f"agents to {my} reply")
        st = deliver_prompt(m, pane, msg)
        if st == "delivered":
            print(f"shares: 已投递,目标已开始处理(target={m}:{pane}, key={key})")
        else:
            eprint(f"shares: 投递 {st}({m}:{pane})key={key}")
        emit_ok({"status": st, "target": f"{m}:{pane}", "key": key, "name": base})
        if st != "delivered":
            sys.exit(1)
    else:
        die("usage", f"未知动词「{verb}」;--llms 看手册", rc=2)

def _my_cell() -> dict | None:
    """本进程所在格:优先 CLAUDE_CODE_SESSION_ID 直配 herdr agent_session(精确,无 cwd 歧义);
    缺则 cwd 唯一命中兜底(多格同 cwd = 歧义 None)。对齐核验 F6 根修。"""
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
    ags = _agents_of(None)
    if sid:
        for a in ags:
            v = a.get("agent_session")
            if (isinstance(v, dict) and v.get("value") == sid) or v == sid:
                return a
    cwd = os.getcwd()
    hits = [a for a in ags if a.get("cwd") == cwd]
    return hits[0] if len(hits) == 1 else None

def _my_alias() -> str | None:
    """本格的 agent 别名(名即消息面路由键);无格或无名 = None。"""
    c = _my_cell()
    return c.get("name") if c and c.get("name") else None

def caller_pane() -> str:
    """本机格 pane id(presence 键等窗格操作面专用);身份判定同 _my_cell。"""
    c = _my_cell()
    return c.get("pane_id", "unknown") if c else "unknown"

def caller_addr() -> str:
    """调用方回信地址(双轨制,用户令 2026-10-15:消息收发用 机:agent别名,
    窗格操作才用 机:格)。身份 = CLAUDE_CODE_SESSION_ID 直配 herdr agent_session
    (精确),cwd 唯一命中兜底;名即路由键;真 hostname 永不进路由位。"""
    c = _my_cell()
    # wsl 伪机自报修正:WSL 继承 win 的 ts 名(host_label=lan-win),但发话格在
    # wsl herdr 实例里;信封机段必须是收方可路由的 wsl,否则回信被 win 当本机格
    mach = "wsl" if (os.name != "nt" and core.win_herdr_ok()) else host_label()
    if c:
        if c.get("name"):
            return f"{mach}:{c['name']}"
        eprint(f"agents: 发话格 {c.get('pane_id')} 无别名,信封退化 机:格 形(正名:herdr agent rename)")
        return f"{mach}:{c.get('pane_id','')}"
    eprint("agents: 调用方所在格未定(session 未配且 cwd 无唯一命中),回信地址退化为机名")
    return mach

# ---------- streams 域 ----------

def streams_main():
    from .cli import parse, setup, handle_globals, manual
    g, verb, pos = parse(sys.argv[1:])
    setup("streams", g)
    handle_globals(g, manual("streams"))
    verb = verb or "view"

    # room 抽象(用户令 2026-10-15):房间即流的前概念,动词面按房间思考
    # streams rooms        -> 列房间(room/* 加 fleet 加 dm/* 计数)
    # streams room <房>    -> 读房(= view room/<房>;fleet 直达)
    # streams room <房> <消息> -> 在房里说话(= append room/<房>,host 前缀自动带)
    # streams dm <别名> <消息> -> 私信专线(流名 dm/<a>/<b>,按名排序两侧)
    if verb == "rooms":
        rooms = {}
        for x in s5_tail_streams():
            n = x.get("name", "")
            if n == "fleet":
                rooms[n] = "全舰队回执主频道"
            elif n.startswith("room/"):
                rooms[n[5:]] = "房间"
            elif n.startswith("dm/"):
                rooms.setdefault("dm", "私信专线族:" + str(1 + rooms.get("dm", "私信专线族:0").split(":")[-1].strip() and int(rooms.get("dm", "私信专线族:0").split(":")[-1]) or 0)) if "dm" in rooms else rooms.update({"dm": "私信专线 1 条"})
        if not rooms:
            print("(无在册房间;room <名> <消息> 说第一句即建)")
        for n, d in rooms.items():
            print(f"{n:<28} {d}")
        return
    def _file_slice(pos: list[str]) -> tuple[str, str]:
        """--file <文件> [--lines N:M] 抽出:上传入 S3,回 (正文附注, 余参数)。
        日志类文件不整读入消息体:消息只带键引用与切片区间,取用行可直达。"""
        from .cli import _val as _v
        fp = _v(pos, "--file", "")
        if not fp:
            return "", pos
        lines = _v(pos, "--lines", "")
        rest = [p for i, p in enumerate(pos)
                if p not in ("--file", "--lines")
                and (i == 0 or pos[i - 1] not in ("--file", "--lines"))]
        if not os.path.isfile(fp):
            die("usage", f"文件不存在:{fp}", rc=2)
        total = sum(1 for _ in open(fp, "rb"))
        key = shares_put(fp)
        span = f"行 {lines}(共 {total})" if lines else f"共 {total} 行"
        note = f"[文件] {os.path.basename(fp)} -> {key}({span});取文件 shares get {key}"
        eprint(f"streams: 文件已上架 {key}({span})")
        return note, rest

    if verb == "room":
        if not pos:
            die("usage", "room <房名> [消息] [-f] [--file <文件> [--lines N:M]]", rc=2)
        room = pos[0]
        stream = room if room == "fleet" else f"room/{room}"
        if "-f" in pos or "--follow" in pos:
            pos = [p0 for p0 in pos if p0 not in ("-f", "--follow")]
            verb, pos = "view", [stream, "-f"]
        elif len(pos) >= 2:
            note, rest = _file_slice(pos)
            text = " ".join(rest[1:]) if len(rest) >= 2 else ""
            body = " | ".join(x for x in (text, note) if x) or note
            verb, pos = "append", [stream, body]
        else:
            verb, pos = "view", [stream]
    elif verb == "dm":
        if len(pos) < 2:
            die("usage", "dm <对方别名> <消息> [--file <文件> [--lines N:M]]", rc=2)
        peer = pos[0]
        me = _my_alias() or host_label()
        pair = sorted([me, peer])
        stream = f"dm/{pair[0]}/{pair[1]}"
        note, rest = _file_slice(pos)
        text = " ".join(rest[1:]) if len(rest) >= 2 else ""
        body = " | ".join(x for x in (text, note) if x) or note
        verb, pos = "append", [stream, body]

    if verb == "view":
        if "-f" in pos or "--follow" in pos:
            stream = next((p0 for p0 in pos if not p0.startswith("-")), "")
            if not stream:
                die("usage", "view <流名> -f(流式跟随,Ctrl+C 退 130)", rc=2)
            import subprocess as sp
            r = sp.call(core.s5_cmd() + ["tail", stream, "-f"])  # 活透传不捕获
            sys.exit(130 if r in (130, 2) else r)
        stream = pos[0] if pos else None
        seq = None
        n = 100
        resume = "--resume" in pos
        if "--from" in pos and pos.index("--from") + 1 < len(pos):
            seq = int(pos[pos.index("--from") + 1])
        for flag in ("-n", "--lines"):
            if flag in pos and pos.index(flag) + 1 < len(pos):
                n = int(pos[pos.index(flag) + 1])
                break
        if resume:
            cur = os.path.expanduser(os.path.join("~/.local/state/prim/cursor", stream))
            if os.path.isfile(cur):
                seq = int(open(cur).read().strip() or "0")
        print("-- 流列表:")
        for x in s5_tail_streams():
            print(json.dumps(x, ensure_ascii=False))
        if stream:
            rows = s5_tail(stream, n, seq)
            print(f"-- 流「{stream}」读({f'from={seq} ' if seq is not None else ''}最近 {n}):")
            for x in rows:
                print(json.dumps(x, ensure_ascii=False))
            last = rows[-1].get("seq_num") if rows else None
            if last is not None:
                cur = os.path.expanduser(os.path.join("~/.local/state/prim/cursor", stream))
                os.makedirs(os.path.dirname(cur), exist_ok=True)  # 流名含斜杠时父链全建
                open(cur, "w").write(str(last))
    elif verb == "append":
        if len(pos) < 2:
            # 流式会话(S2 范式):无消息 = stdin 逐行追加(cat x | streams append <流>)
            if len(pos) == 1:
                import subprocess as sp
                r = sp.call(core.s5_cmd() + ["append", pos[0]])  # stdin 直通
                sys.exit(r)
            die("usage", "append <流> <消息>(或 stdin 管道:cat x | streams append <流>)", rc=2)
        body = f"{host_label()}|{pos[1]}"
        if s5_append(pos[0], body):
            print(f"streams: 已追加 → {pos[0]}")
            emit_ok({"status": "delivered", "stream": pos[0]})
        else:
            die("engine_fail", "s5 append 失败", rc=1)
    elif verb == "to":
        if len(pos) < 3:
            die("usage", "to <id> <流> <消息> [--force]", rc=2)
        m, pane = resolve(pos[0])
        stream, body = pos[1], pos[2]
        blocked = gate(m, pane)
        if blocked:
            s5_append(f"room/deferred/{pane}", f"{host_label()}|mode=deferred|domain=streams|流 {stream} 消息待递(--force 重发)")
            eprint(f"streams: 目标存在操作对话框,已拒投并代记")
            emit_ok({"status": "deferred", "target": f"{m}:{pane}", "stream": stream})
            sys.exit(1)
        if not s5_append(stream, f"{host_label()}|{body}"):
            die("engine_fail", "s5 append 失败", rc=1)
        src = caller_addr()
        src_host, src_pane = (src.split(":", 1) + [""])[:2]
        from .msg import MsgEnvelope
        env = MsgEnvelope(domain="streams", src_host=src_host, src_pane=src_pane,
                          dst=pos[0], stream=stream, body=body)
        my = _my_alias() or f"{src_host}:{src_pane}"
        msg = env.render(f"agents to {my} reply (stream {stream} attached)")
        st = deliver_prompt(m, pane, msg)
        if st == "delivered":
            print(f"streams: 已投递,目标已开始处理(target={m}:{pane}, stream={stream})")
        else:
            eprint(f"streams: 投递状态 {st}(target={m}:{pane})")
        emit_ok({"status": st, "target": f"{m}:{pane}", "stream": stream})
        if st != "delivered":
            sys.exit(1)
    else:
        die("usage", f"未知动词「{verb}」;--llms 看手册", rc=2)

def s5_tail_streams() -> list[dict]:
    r = s5_run("streams")
    out = []
    for line in (r.stdout or "").splitlines()[:30]:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return out

# ---------- tasks 域 ----------

def tasks_main():
    from .cli import parse, setup, handle_globals, manual
    g, verb, pos = parse(sys.argv[1:])
    setup("tasks", g)
    handle_globals(g, manual("tasks"))
    verb = verb or "view"

    if verb == "view":
        # 实时任务面(用户令 2026-10-14:不看历史事件,看各格现在跑什么任务)
        # 上半 = fleet 状态总览(herdr 面,含远机);下半 = 本机各仓 hst task show 直读;
        # 远机任务文本不经 ssh(零 ssh 纪律),经 agents read <id> 读屏即得(L4 行自带任务摘要)
        machine = pos[0] if pos else None
        ags = _agents_of(None if machine in (None, "local") else machine)
        if not machine:
            fleet = [("local", a) for a in ags]
            for lab in _machine_labels():
                fleet += [(lab, a) for a in _agents_of(lab)]
        else:
            fleet = [("local" if machine == "local" else machine, a) for a in ags]
        print(f"{'':<1}{'HOST':<12} {'NAME':<24} {'ST':<5} CWD")
        for host, a in fleet:
            if not a.get("agent"):
                continue
            st = a.get("agent_status", "")
            mark = "*" if st == "working" else " "
            print(f"{mark}{host:<12}{a.get('name') or a.get('pane_id',''):<24}[{st[:4]}] {a.get('cwd','')}")
        print("-- 本机实时任务(hst task show 直读;远机任务经 agents read <id> 看屏):")
        for host, a in fleet:
            if not a.get("agent") or host != "local":
                continue
            cwd = a.get("cwd") or ""
            if not cwd or cwd == os.path.expanduser("~") or not os.path.isdir(cwd):
                continue
            try:
                ag = a.get("agent") or "claude"
                if os.name == "nt":
                    rp = subprocess.run(["hst", "task", "show", "--agent", ag], capture_output=True, text=True,
                                        cwd=cwd, timeout=10, encoding="utf-8", errors="replace")
                else:
                    rp = subprocess.run(["bash", "-lc", f"hst task show --agent {ag}"], capture_output=True, text=True,
                                        cwd=cwd, timeout=10, encoding="utf-8", errors="replace")
            except subprocess.TimeoutExpired:
                continue
            out = (rp.stdout or "").strip()
            if out:
                # 2.15.0 show 首行恒 present 旗;取 task.text 行见「在跑什么」(漂移单 D6)
                tl = next((l for l in out.splitlines() if "task.text" in l), "")
                shown = tl[:100] if tl else ("(无 task)" if "present=false" in out.splitlines()[0] else out.splitlines()[0][:100])
                print(f"  {a.get('name') or a.get('pane_id','')}: {shown}")
    elif verb in ("set", "to"):
        if len(pos) < 2:
            die("usage", f"{verb} <id> <文本>", rc=2)
        m, pane = resolve(pos[0])
        text = " ".join(pos[1:])
        # F7 修:D9 裁 set 只写不扰 —— 门控只归 to;set 直写(目标有对话框也照设)
        blocked = gate(m, pane) if verb == "to" else False
        if blocked:
            s5_append(f"room/deferred/{pane}", f"{host_label()}|mode=deferred|domain=tasks|任务「{text}」待设(--force 重发)")
            eprint(f"tasks: 目标存在操作对话框,已拒投并代记")
            emit_ok({"status": "deferred", "target": f"{m}:{pane}"})
            sys.exit(1)
        cwd = pane_cwd(m, pane)
        _kind = next((x.get("agent") or "claude" for x in _agents_of(None if m in ("", "local") else m)
                      if x.get("pane_id") == pane), "claude")
        _hst_task_set(m, cwd, text, _kind)
        if verb == "set":
            # D9(2026-10-15 裁):set = OPERATE 只写不扰;知会归 to(三段文法)
            emit_ok({"status": "delivered", "target": f"{m}:{pane}", "task": text})
            return
        src = caller_addr()
        src_host, src_pane = (src.split(":", 1) + [""])[:2]
        from .msg import MsgEnvelope
        env = MsgEnvelope(domain="tasks", src_host=src_host, src_pane=src_pane,
                          dst=pos[0], cwd=cwd, body=text)
        msg = env.render("tasks view")
        st = deliver_prompt(m, pane, msg)
        print(f"tasks: 已设置(target={m}, cwd={cwd})" + (f" 并投出" if st == "delivered" else f";投递 {st}"))
        emit_ok({"status": st, "target": f"{m}:{pane}", "cwd": cwd})
    else:
        die("usage", f"未知动词「{verb}」;--llms 看手册", rc=2)

def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")

def _hst_task_set(machine: str, cwd: str, text: str, agent: str = "claude"):
    """hst task set(本机直跑,--agent 会话隔离;远机走 pending 流 + apply 受体)。"""
    import shlex
    if machine in ("", "local"):
        if os.name == "nt":
            # win 直跑 hst.exe + cwd 参(同 view nt 分支;bash 包装道在 win 解析到
            # WSL bash 会翻车,/d/ 与 /mnt/ 形皆非 git-bash,弃)
            r = subprocess.run(["hst", "task", "set", "--agent", agent, text],
                               capture_output=True, text=True, cwd=cwd, timeout=15,
                               encoding="utf-8", errors="replace")
        else:
            r = subprocess.run(["bash", "-lc", f"hst task set --agent {shlex.quote(agent)} {shlex.quote(text)}"],
                               capture_output=True, text=True, cwd=cwd, timeout=15,
                               encoding="utf-8", errors="replace")
        if r.returncode != 0:
            die("engine_fail", f"hst task set 失败:{(r.stderr or '')[:100]}")
    else:
        # 协议形:pending 流 + plugin action 唤醒(零 ssh)
        tid = str(time.time_ns())
        s5_append(f"tasks/pending/{machine}", f"{host_label()}|{text}|{cwd}|{tid}|{agent}")
        herdr_run(machine, "plugin", "action", "invoke", "apply", "--plugin", "tasks")

_FW_CACHE: bool | None = None

def _fw_ok() -> bool:
    """win 面 tailcat 防火墙放行检测(缓存;规则名 tailcat-in,由 CTA 指令创建)。"""
    global _FW_CACHE
    if os.name != "nt":
        return True
    if _FW_CACHE is None:
        try:
            r = subprocess.run(["netsh", "advfirewall", "firewall", "show", "rule",
                                "name=tailcat-in"], capture_output=True, text=True,
                               timeout=8, encoding="utf-8", errors="replace")
            _FW_CACHE = (r.returncode == 0 and "tailcat" in (r.stdout or "").lower())
        except Exception:
            _FW_CACHE = True  # 检测失败不挡操作,只少一条提醒
    return _FW_CACHE

def _fw_cta():
    """win 防火墙未放行时的 CTA 提醒(stderr 面,--json 亦可见)。"""
    if _fw_ok():
        return
    tc = _tailcat()
    eprint("warn: windows 防火墙未见 tailcat 放行规则(默认入站 Block,对方直连会被拦,仅 DERP 中继可达)")
    eprint(f'CTA: 管理员运行: netsh advfirewall firewall add rule name=tailcat-in dir=in action=allow program="{tc}" enable=yes profile=any')

# ---------- pipes 域(tailcat 实时管道:本机收对方发) ----------

def _tailcat() -> str:
    b = core._find_bin("tailcat")
    if not b:
        die("engine_fail", "本机无 tailcat(v0.7.0)", rc=1)
    return b

def _pdir() -> str:
    d = os.path.expanduser("~/.local/state/pipe")
    os.makedirs(d, exist_ok=True)
    return d

def pipes_broadcast(pid: int, alive: int):
    """公开行(契约五a:跨机可见,不含 addr)。"""
    s5_append("room/pipe-live", f"{host_label()}|pid={pid}|alive={alive}|ts={_now()}")

def _pid_alive(pid: int) -> bool:
    """跨平台活性探测(win 上 os.kill(pid,0) 是 TerminateProcess,禁用)。"""
    if os.name == "nt":
        try:
            import ctypes
            k32 = ctypes.windll.kernel32
            h = k32.OpenProcess(0x1000, False, int(pid))  # PROCESS_QUERY_LIMITED_INFORMATION
            if not h:
                return False
            k32.CloseHandle(h)
            return True
        except Exception:
            return False
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True

def pipes_alive() -> list[dict]:
    """本机活动管道:清死档(pid 不活即收档),返回 [{pid,addr,log}]。"""
    d = _pdir()
    out = []
    import glob as _g
    for pf in sorted(_g.glob(os.path.join(d, "pid.*.txt"))):
        pid = os.path.basename(pf)[4:-4]
        try:
            pid_i = int(pid)
        except ValueError:
            continue
        if not _pid_alive(pid_i):
            for suf in ("pid", "addr", "log"):
                try:
                    os.remove(os.path.join(d, f"{suf}.{pid}.txt"))
                except OSError:
                    pass
            continue
        addr = ""
        try:
            addr = open(os.path.join(d, f"addr.{pid}.txt")).read().strip()
        except OSError:
            pass
        out.append({"pid": pid_i, "addr": addr, "log": os.path.join(d, f"log.{pid}.txt")})
    return out

def pipes_open() -> tuple[int, str]:
    """起收听(后台,常驻至 close),返回 (pid, addr);状态档 pid/addr/log 三件。"""
    d = _pdir()
    tc = _tailcat()
    addr_file = os.path.join(d, f"_open.addr")
    log_file = os.path.join(d, f"_open.log")
    env = dict(os.environ, TAILCAT_ADDR_FILE=addr_file)
    with open(log_file, "wb") as lg:
        p = subprocess.Popen([tc], stdout=lg, stderr=subprocess.STDOUT,
                             stdin=subprocess.DEVNULL, env=env,
                             start_new_session=True)
    addr = ""
    for _ in range(10):
        if os.path.isfile(addr_file) and os.path.getsize(addr_file) > 0:
            addr = open(addr_file).read().strip()
            break
        try:
            r = subprocess.run(["grep", "-oE", r"tc[A-Za-z0-9_-]{20,}", log_file],
                               capture_output=True, text=True, timeout=5)
            addr = (r.stdout or "").splitlines()[0].strip() if r.stdout.strip() else ""
        except Exception:
            addr = ""
        if addr:
            break
        time.sleep(1)
    pid = p.pid
    if addr:
        try:
            os.replace(addr_file, os.path.join(d, f"addr.{pid}.txt"))
        except OSError:
            pass
        log_dst = os.path.join(d, f"log.{pid}.txt")
        try:
            os.replace(log_file, log_dst)
        except OSError:
            # win:子进程握 log 句柄,replace 拒;快照代位(活文件仍 _open.log)
            try:
                import shutil as _sh
                _sh.copyfile(log_file, log_dst)
            except OSError:
                pass
        open(os.path.join(d, f"pid.{pid}.txt"), "w").close()
        pipes_broadcast(pid, 1)
    else:
        p.kill()
        eprint("pipes: 地址未取到(10s)")
    return pid, addr

def pipes_view(machine: str | None):
    if machine:
        rows = [x for x in s5_tail("room/pipe-live", 30)
                if str(x.get("body", "")).startswith(f"{machine}|pid=")]
        print(f"-- {machine} 管道公开行(room/pipe-live,无地址):")
        for x in rows[-8:]:
            print(f"  {x.get('body')}")
        if not rows:
            print("  (无)")
        return
    from .cli import agents_view
    agents_view(None)
    print("-- 本机活动管道:")
    rows = pipes_alive()
    for r in rows:
        print(f"pid={r['pid']} addr={r['addr']} log={r['log']}")
    if not rows:
        print("  (无)")

def pipes_main():
    from .cli import parse, setup, handle_globals, manual
    g, verb, pos = parse(sys.argv[1:])
    setup("pipes", g)
    handle_globals(g, manual("pipes"))
    verb = verb or "view"

    if verb == "view":
        pipes_view(pos[0] if pos else None)
    elif verb == "open":
        if "--keep" in pos:
            die("usage", "pipes 无 --keep(管道常驻至 close)", rc=2)
        pid, addr = pipes_open()
        if addr:
            print(f"pipes: 已开 addr={addr}(日志见 {_pdir()}/log.{pid}.txt)")
            _fw_cta()
            emit_ok({"status": "delivered", "addr": addr, "pid": pid})
        else:
            die("engine_fail", "tailcat 地址未取到", rc=1)
    elif verb == "close":
        if not pos:
            die("usage", "close <地址或pid>", rc=2)
        q = pos[0]
        hit = next((r for r in pipes_alive()
                    if str(r["pid"]) == q or r["addr"] == q), None)
        if not hit:
            die("not_found", f"未匹配管道({q})", [{"command": "pipes view", "description": "查本机管道"}])
        try:
            os.kill(hit["pid"], 15)
        except OSError:
            pass
        for suf in ("pid", "addr", "log"):
            try:
                os.remove(os.path.join(_pdir(), f"{suf}.{hit['pid']}.txt"))
            except OSError:
                pass
        pipes_broadcast(hit["pid"], 0)
        print(f"pipes: 已关 pid={hit['pid']}(地址作废)")
        emit_ok({"status": "delivered", "pid": hit["pid"]})
    elif verb == "send":
        # 收方动词(2026-10-15 用户令关缺口):连对方管道发数据,stdin 直通;
        # 引擎 tailcat 藏进原语,取用行不再漏引擎名
        if not pos:
            die("usage", "send <addr>(pipe stdin to the peer;e.g. echo x | pipes send <addr>)", rc=2)
        import subprocess as sp
        sys.exit(sp.call([_tailcat(), pos[0]]))
    elif verb == "to":
        if "--keep" in pos:
            die("usage", "pipes 无 --keep(管道常驻至 close)", rc=2)
        if not pos:
            die("usage", "to <id> [--force](=open+模板知会)", rc=2)
        m, pane = resolve(pos[0])
        blocked = gate(m, pane)
        pid, addr = pipes_open()
        if not addr:
            die("engine_fail", "tailcat 地址未取到(管道未开)", rc=1)
        _fw_cta()
        if blocked:
            s5_append(f"room/deferred/{pane}", f"{host_label()}|mode=deferred|domain=pipes|管道 {addr} 待达(--force 重发)")
            eprint(f"pipes: 目标存在操作对话框,已拒投;管道已开启 addr={addr};已代记")
            emit_ok({"status": "deferred", "target": f"{m}:{pane}", "addr": addr})
            sys.exit(1)
        src = caller_addr()
        src_host, src_pane = (src.split(":", 1) + [""])[:2]
        from .msg import MsgEnvelope
        env = MsgEnvelope(domain="pipes", src_host=src_host, src_pane=src_pane,
                          dst=pos[0], addr=addr)
        msg = env.render(f"pipes send {addr}")
        st = deliver_prompt(m, pane, msg)
        if st == "delivered":
            print(f"pipes: 已投递(target={m}:{pane})(addr={addr};pid={pid};关闭:pipes close {addr};发数据:pipes send {addr})")
        else:
            eprint(f"pipes: 投递状态 {st}(target={m}:{pane}, addr={addr})")
        emit_ok({"status": st, "target": f"{m}:{pane}", "addr": addr, "pid": pid})
        if st != "delivered":
            sys.exit(1)
    else:
        die("usage", f"未知动词「{verb}」;--llms 看手册", rc=2)


# ---------- ports 域(任意节点端口转发映射:tailcat serve) ----------

def _podir() -> str:
    d = os.path.expanduser("~/.local/state/ports")
    os.makedirs(d, exist_ok=True)
    return d

def ports_broadcast(pid: int, alive: int):
    """公开行(契约五a:跨机可见,不含 addr)。"""
    s5_append("room/port-live", f"{host_label()}|pid={pid}|alive={alive}|ts={_now()}")

def ports_alive() -> list[dict]:
    """本机活动端口映射:清死档(pid 不活即收档),返回 [{pid,addr,spec,log}]。"""
    d = _podir()
    out = []
    import glob as _g
    for pf in sorted(_g.glob(os.path.join(d, "pid.*.txt"))):
        pid = os.path.basename(pf)[4:-4]
        try:
            pid_i = int(pid)
        except ValueError:
            continue
        if not _pid_alive(pid_i):
            for suf in ("pid", "addr", "log", "spec"):
                try:
                    os.remove(os.path.join(d, f"{suf}.{pid}.txt"))
                except OSError:
                    pass
            continue
        addr = ""
        spec = ""
        try:
            addr = open(os.path.join(d, f"addr.{pid}.txt")).read().strip()
        except OSError:
            pass
        try:
            spec = open(os.path.join(d, f"spec.{pid}.txt")).read().strip()
        except OSError:
            pass
        out.append({"pid": pid_i, "addr": addr, "spec": spec,
                    "log": os.path.join(d, f"log.{pid}.txt")})
    return out

def _use_line(spec: str, addr: str) -> str:
    """取用行(grok F1 修):数字 spec 全端口枚举成可执行 forward;非数字 spec(all/
    exit-node)无 concrete 客户端口可代选,出指引形(exit-node 远端 = ip:port)。"""
    ports = []
    for part in spec.split(","):
        head = part.split(":")[0]
        if head.isdigit():
            ports.append(head)
    if ports:
        return "ports fwd " + addr + " " + " ".join(f"0:{p}" for p in ports)
    if spec == "exit-node":
        return f"ports fwd {addr} 0:<server-ip>:<port>"
    return f"ports fwd {addr} 0:<port>"

def ports_open(spec: str) -> tuple[int, str]:
    """起端口转发映射(后台 tailcat serve <spec>),返回 (pid, addr);状态档 pid/addr/log/spec 四件。"""
    d = _podir()
    tc = _tailcat()
    addr_file = os.path.join(d, "_open.addr")
    log_file = os.path.join(d, "_open.log")
    env = dict(os.environ, TAILCAT_ADDR_FILE=addr_file)
    with open(log_file, "wb") as lg:
        p = subprocess.Popen([tc, "serve", spec], stdout=lg, stderr=subprocess.STDOUT,
                             stdin=subprocess.DEVNULL, env=env,
                             start_new_session=True)
    addr = ""
    for _ in range(10):
        if os.path.isfile(addr_file) and os.path.getsize(addr_file) > 0:
            addr = open(addr_file).read().strip()
            break
        try:
            r = subprocess.run(["grep", "-oE", r"tc[A-Za-z0-9_-]{20,}", log_file],
                               capture_output=True, text=True, timeout=5)
            addr = (r.stdout or "").splitlines()[0].strip() if r.stdout.strip() else ""
        except Exception:
            addr = ""
        if addr:
            break
        time.sleep(1)
    pid = p.pid
    if addr:
        try:
            os.replace(addr_file, os.path.join(d, f"addr.{pid}.txt"))
        except OSError:
            pass
        log_dst = os.path.join(d, f"log.{pid}.txt")
        try:
            os.replace(log_file, log_dst)
        except OSError:
            # win:子进程握 log 句柄,replace 拒;快照代位(活文件仍 _open.log)
            try:
                import shutil as _sh
                _sh.copyfile(log_file, log_dst)
            except OSError:
                pass
        open(os.path.join(d, f"pid.{pid}.txt"), "w").close()
        open(os.path.join(d, f"spec.{pid}.txt"), "w").write(spec)
        ports_broadcast(pid, 1)
    else:
        p.kill()
        eprint("ports: 地址未取到(10s)")
    return pid, addr

def ports_view(machine: str | None):
    if machine:
        rows = [x for x in s5_tail("room/port-live", 30)
                if str(x.get("body", "")).startswith(f"{machine}|pid=")]
        print(f"-- {machine} 端口映射公开行(room/port-live,无地址):")
        for x in rows[-8:]:
            print(f"  {x.get('body')}")
        if not rows:
            print("  (无)")
        return
    from .cli import agents_view
    agents_view(None)
    print("-- 本机活动端口映射:")
    rows = ports_alive()
    for r in rows:
        print(f"pid={r['pid']} spec={r['spec']} addr={r['addr']} log={r['log']}")
    if not rows:
        print("  (无)")

def ports_main():
    from .cli import parse, setup, handle_globals, manual
    g, verb, pos = parse(sys.argv[1:])
    setup("ports", g)
    handle_globals(g, manual("ports"))
    verb = verb or "view"

    if verb == "view":
        ports_view(pos[0] if pos else None)
    elif verb == "open":
        if "--keep" in pos:
            die("usage", "ports 无 --keep(映射常驻至 close,无超时自关)", rc=2)
        if not pos:
            die("usage", "open <spec>(spec = 8080,8443 端口表 / 5555:IP:5555 服务侧映射 / all / exit-node)", rc=2)
        spec = ",".join(pos)
        pid, addr = ports_open(spec)
        if addr:
            print(f"ports: 已开 spec={spec} addr={addr}(日志见 {_podir()}/log.{pid}.txt)")
            _fw_cta()
            emit_ok({"status": "delivered", "spec": spec, "addr": addr, "pid": pid})
        else:
            die("engine_fail", "tailcat 地址未取到", rc=1)
    elif verb == "close":
        if not pos:
            die("usage", "close <地址或pid>", rc=2)
        q = pos[0]
        hit = next((r for r in ports_alive()
                    if str(r["pid"]) == q or r["addr"] == q), None)
        if not hit:
            die("not_found", f"未匹配端口映射({q})", [{"command": "ports view", "description": "查本机端口映射"}])
        try:
            os.kill(hit["pid"], 15)
        except OSError:
            pass
        for suf in ("pid", "addr", "log", "spec"):
            try:
                os.remove(os.path.join(_podir(), f"{suf}.{hit['pid']}.txt"))
            except OSError:
                pass
        ports_broadcast(hit["pid"], 0)
        print(f"ports: 已关 pid={hit['pid']}(地址作废)")
        emit_ok({"status": "delivered", "pid": hit["pid"]})
    elif verb == "fwd":
        # 收方动词(2026-10-15 用户令关缺口):本地起听转发到对方映射口;
        # 引擎 tailcat 藏进原语;Ctrl+C 停
        if len(pos) < 2:
            die("usage", "fwd <addr> <local>:<remote-port> ...(local listener;0 = free port;Ctrl+C to stop)", rc=2)
        import subprocess as sp
        sys.exit(sp.call([_tailcat(), "forward", *pos]))
    elif verb == "to":
        if "--keep" in pos:
            die("usage", "ports 无 --keep(映射常驻至 close,无超时自关)", rc=2)
        spec_args = [x for x in pos if x != "--force"]
        if len(spec_args) < 2:
            die("usage", "to <id> <spec> [--force](=open+模板知会)", rc=2)
        spec = ",".join(spec_args[1:])
        m, pane = resolve(spec_args[0])
        blocked = gate(m, pane)
        pid, addr = ports_open(spec)
        if not addr:
            die("engine_fail", "tailcat 地址未取到(映射未开)", rc=1)
        _fw_cta()
        use = _use_line(spec, addr)
        if blocked:
            s5_append(f"room/deferred/{pane}", f"{host_label()}|mode=deferred|domain=ports|端口映射 {addr}({spec}) 待达(--force 重发)")
            eprint(f"ports: 目标存在操作对话框,已拒投;映射已开 addr={addr};已代记")
            emit_ok({"status": "deferred", "target": f"{m}:{pane}", "addr": addr})
            sys.exit(1)
        src = caller_addr()
        src_host, src_pane = (src.split(":", 1) + [""])[:2]
        from .msg import MsgEnvelope
        env = MsgEnvelope(domain="ports", src_host=src_host, src_pane=src_pane,
                          dst=spec_args[0], addr=addr, body=f"opened port mapping {spec}")
        msg = env.render(use)
        st = deliver_prompt(m, pane, msg)
        if st == "delivered":
            print(f"ports: 已投递(target={m}:{pane})(addr={addr};spec={spec};pid={pid};关闭:ports close {addr})")
        else:
            eprint(f"ports: 投递状态 {st}(target={m}:{pane}, addr={addr})")
        emit_ok({"status": st, "target": f"{m}:{pane}", "addr": addr, "spec": spec, "pid": pid})
        if st != "delivered":
            sys.exit(1)
    else:
        die("usage", f"未知动词「{verb}」;--llms 看手册", rc=2)
