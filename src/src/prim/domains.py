"""prim 四域实现(shares/streams/tasks/pipes)——v3 python 形

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
        msg = env.render(f"s5 get -o {base} {key}")
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

def caller_addr() -> str:
    """调用方回信地址:cwd 匹配本机格 → host:pane;多格同 cwd 时标歧义不猜(evo 批判例 w8:p4);
    退化 host(此时取用行不可直答,信封渲染层告警)。"""
    cwd = os.getcwd()
    hits = [a for a in _agents_of(None) if a.get("cwd") == cwd]
    if len(hits) == 1:
        return f"{host_label()}:{hits[0].get('pane_id','')}"
    if len(hits) > 1:
        names = ", ".join(f"{a.get('pane_id')}" for a in hits)
        eprint(f"agents: 同 cwd 多格({names}),回信地址歧义不猜;取用行需调用方自行补 机:格")
        return host_label()
    eprint("agents: 调用方不在 agent 格内(cwd 无格匹配),回信地址退化为机名;取用行需调用方自行补 机:格")
    return host_label()

# ---------- streams 域 ----------

def streams_main():
    from .cli import parse, setup, handle_globals, manual
    g, verb, pos = parse(sys.argv[1:])
    setup("streams", g)
    handle_globals(g, manual("streams"))
    verb = verb or "view"

    if verb == "view":
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
            die("usage", "append <流> <消息>", rc=2)
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
        msg = env.render(f"s5 tail {stream}")
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
                if os.name == "nt":
                    rp = subprocess.run(["hst", "task", "show"], capture_output=True, text=True,
                                        cwd=cwd, timeout=10, encoding="utf-8", errors="replace")
                else:
                    rp = subprocess.run(["bash", "-lc", "hst task show"], capture_output=True, text=True,
                                        cwd=cwd, timeout=10, encoding="utf-8", errors="replace")
            except subprocess.TimeoutExpired:
                continue
            out = (rp.stdout or "").strip()
            if out:
                print(f"  {a.get('name') or a.get('pane_id','')}: {out.splitlines()[0][:100]}")
    elif verb in ("set", "to"):
        if len(pos) < 2:
            die("usage", f"{verb} <id> <文本>", rc=2)
        m, pane = resolve(pos[0])
        text = " ".join(pos[1:])
        blocked = gate(m, pane)
        if blocked:
            s5_append(f"room/deferred/{pane}", f"{host_label()}|mode=deferred|domain=tasks|任务「{text}」待设(--force 重发)")
            eprint(f"tasks: 目标存在操作对话框,已拒投并代记")
            emit_ok({"status": "deferred", "target": f"{m}:{pane}"})
            sys.exit(1)
        cwd = pane_cwd(m, pane)
        _hst_task_set(m, cwd, text)
        s5_append("tasks/shared", json.dumps({"ts": _now(), "node": m, "cwd": cwd, "by": host_label(), "task": text}, ensure_ascii=False))
        src = caller_addr()
        src_host, src_pane = (src.split(":", 1) + [""])[:2]
        from .msg import MsgEnvelope
        env = MsgEnvelope(domain="tasks", src_host=src_host, src_pane=src_pane,
                          dst=pos[0], cwd=cwd, body=text)
        msg = env.render(f"cd {cwd} && hst task show")
        st = deliver_prompt(m, pane, msg)
        print(f"tasks: 已设置(target={m}, cwd={cwd})" + (f" 并投出" if st == "delivered" else f";投递 {st}"))
        emit_ok({"status": st, "target": f"{m}:{pane}", "cwd": cwd})
    else:
        die("usage", f"未知动词「{verb}」;--llms 看手册", rc=2)

def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")

def _hst_task_set(machine: str, cwd: str, text: str):
    """hst task set(本机直跑;远机走 pending 流 + apply 受体)。"""
    import shlex
    if machine in ("", "local"):
        r = subprocess.run(["bash", "-c", f"cd {shlex.quote(cwd)} && hst task set {shlex.quote(text)} || hst goal set {shlex.quote(text)}"],
                           capture_output=True, text=True, timeout=15)
    else:
        # 协议形:pending 流 + plugin action 唤醒(零 ssh)
        tid = str(time.time_ns())
        s5_append(f"tasks/pending/{machine}", f"{host_label()}|{text}|{cwd}|{tid}")
        herdr_run(machine, "plugin", "action", "invoke", "apply", "--plugin", "tasks")

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

def pipes_open(keep: bool = False) -> tuple[int, str]:
    """起收听(后台),返回 (pid, addr);状态档 pid/addr/log 三件。"""
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
        for src, dst in ((addr_file, os.path.join(d, f"addr.{pid}.txt")),
                         (log_file, os.path.join(d, f"log.{pid}.txt"))):
            try:
                os.replace(src, dst)
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
        keep = "--keep" in pos
        pid, addr = pipes_open(keep)
        if addr:
            print(f"pipes: 已开 addr={addr}(日志见 {_pdir()}/log.{pid}.txt)")
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
    elif verb == "to":
        if not pos:
            die("usage", "to <id> [--force](=open+模板知会)", rc=2)
        m, pane = resolve(pos[0])
        blocked = gate(m, pane)
        pid, addr = pipes_open()
        if not addr:
            die("engine_fail", "tailcat 地址未取到(管道未开)", rc=1)
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
        msg = env.render(f"tailcat {addr}")
        st = deliver_prompt(m, pane, msg)
        if st == "delivered":
            print(f"pipes: 已投递(target={m}:{pane})(addr={addr};pid={pid};关闭:pipes close {addr})")
        else:
            eprint(f"pipes: 投递状态 {st}(target={m}:{pane}, addr={addr})")
        emit_ok({"status": st, "target": f"{m}:{pane}", "addr": addr, "pid": pid})
        if st != "delivered":
            sys.exit(1)
    else:
        die("usage", f"未知动词「{verb}」;--llms 看手册", rc=2)
