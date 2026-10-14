"""prim 域实现(shares/streams)——v3 python 形

各域骑其引擎 s5,DELIVER = 引擎操作 + 模板三行形 + agents to 投递(status 信封)
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
