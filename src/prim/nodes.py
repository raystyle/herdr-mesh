"""machines 域:herdr machine 系列封装(第九原语;2026-10-24 ADR-0007 由 nodes 更名,nodes 留大版本别名)

machine = 舰队节点(ssh 注册的远端 herdr 实例)。动词面与 herdr machine
一一对应:list/status/add/rename/remove/enable/disable/reconnect;机册真源
在 herdr(win 侧),本域是机册管理的原语面(agents.machines 只是只读快照)。
"""
from __future__ import annotations
from . import core
import json
import sys
from .core import die, emit_ok, eprint, herdr_json, herdr_run

# herdr machine 动词透传族(label 寻址优先,profile-id 亦收)
_PASS = {"status", "reconnect", "add", "rename", "remove", "enable", "disable"}


def _machines_raw() -> list[dict]:
    d = herdr_json(None, "machine", "list", "--json")
    if isinstance(d, dict):
        d = d.get("result", {}).get("machines") or d.get("machines") or []
    return [x for x in d if isinstance(x, dict)]


def _lookup(query: str) -> dict | None:
    """label 或 profile-id 寻址一台机。"""
    for m in _machines_raw():
        if m.get("label") == query or m.get("id") == query:
            return m
    return None


def machines_main():
    from .cli import parse, setup, handle_globals, manual
    g, verb, pos = parse(sys.argv[1:])
    setup("nodes", g)
    handle_globals(g, manual("machines"))
    verb = verb or "view"

    if verb in ("pane", "run", "close"):
        # pane 原语族直透(用户令 2026-10-17:nodes 应可操作 pane run 原语)
        # run <节点> <格> <命令...>  |  close <节点> <格>  |  pane <节点> <子面...>
        if verb == "run":
            (len(pos) >= 3) or die("usage", "run <节点> <格> <命令...>(格内跑命令,herdr pane run)", rc=2)
            machine, pane, cmd = pos[0], pos[1], pos[2:]
            r = herdr_run(machine, "pane", "run", pane, *cmd, timeout=60)
            if r.returncode != 0:
                die("engine_fail", (r.stderr or r.stdout or "").strip()[:200], rc=1)
            if (r.stdout or "").strip():
                print(r.stdout.strip()[-1500:])
            emit_ok({"status": "ok", "machine": machine, "pane": pane, "cmd": cmd})
            return
        if verb == "close":
            (len(pos) >= 2) or die("usage", "close <节点> <格>(直关格;agent 在跑请先 agents close 走优雅退场)", rc=2)
            machine, pane = pos[0], pos[1]
            r = herdr_run(machine, "pane", "close", pane, timeout=30)
            if r.returncode != 0:
                die("engine_fail", (r.stderr or r.stdout or "").strip()[:200], rc=1)
            print(f"nodes: 已关 {machine}:{pane}")
            emit_ok({"status": "ok", "machine": machine, "pane": pane, "closed": True})
            return
        # pane <节点> <herdr pane 子面...>:list/get/read/split/send-keys/... 直透
        (len(pos) >= 2) or die("usage", "pane <节点> <子面...>(herdr pane 直透)", rc=2)
        machine = pos[0]
        r = herdr_run(machine, "pane", *pos[1:], timeout=60)
        if r.returncode != 0:
            die("engine_fail", (r.stderr or r.stdout or "").strip()[:200], rc=1)
        out = (r.stdout or "").strip()
        if out:
            print(out[-3000:])
        return

    if verb in ("runtime", "runtimes"):
        # runtime 子面(用户令 2026-10-17:不立新原语,收 nodes 下):agent 运行时环境
        # 检查与管理,骑 ark;栈真源 = 仓根 runtimes.toml(仓 agent 自定);--machine 跨机
        from .runtimes import runtime_main
        runtime_main(pos, g)
        return

    if verb in ("view", "list"):
        # view = list 同面(册表 + 可达性);--json 出原册
        ms = _machines_raw()
        if g.get("json"):
            emit_ok({"status": "ok", "count": len(ms), "machines": ms})
            return
        print(f"{'MACHINE':<14} {'PROFILE-ID':<34} {'SSH':<22} {'SESSION':<10} STATE")
        for m in ms:
            print(f"{(m.get('label') or '-'):<14} {(m.get('id') or '-'):<34} "
                  f"{(m.get('target') or '-'):<22} "
                  f"{(m.get('session') or 'default'):<10} "
                  f"{('enabled' if m.get('enabled', True) else 'disabled')}")
        # 可达性(status 面合并进 view;离线机 fail-soft 不挂整面)
        try:
            st = herdr_json(None, "machine", "status", "--json", timeout=20)
            states = {}
            if isinstance(st, dict):
                st = st.get("result", {}).get("machines") or st.get("machines") or []
            for x in st if isinstance(st, list) else []:
                if isinstance(x, dict):
                    states[x.get("label") or x.get("id")] = x.get("status") or x.get("reachable")
            for m in ms:
                lab = m.get("label")
                if lab in states:
                    print(f"  {lab}: {states[lab]}")
        except Exception:
            eprint("machines: 可达性探测失败(herdr machine status 不可用);单机详查: machines status <名>")
        return

    if verb == "status":
        # 无参 = 全量状态;带参 = 单机(label 或 id)
        args = ["machine", "status"] + (pos if pos else [])
        args += ["--json"]
        r = herdr_run(None, *args, timeout=30)
        if r.returncode != 0:
            die("engine_fail", (r.stderr or r.stdout or "").strip()[:200], rc=1)
        try:
            d = json.loads(r.stdout)
            rows = d.get("result", {}).get("machines") or d.get("machines") or []
        except Exception:
            rows = []
        for x in rows if isinstance(rows, list) else []:
            if isinstance(x, dict):
                print(f"{(x.get('label') or '-'):<14} {x.get('status') or x.get('reachable')}")
        emit_ok({"status": "ok", "count": len(rows)})
        return

    if verb in _PASS:
        # 透传族:add/rename/remove/enable/disable/reconnect/status(上已收)
        # 写面预检:rename/remove/enable/disable 先解析目标(label 补 id)
        args = ["machine", verb]
        if verb in ("rename", "remove", "enable", "disable", "reconnect") and pos:
            m = _lookup(pos[0])
            args += [m.get("id") if m else pos[0]]
            args += pos[1:]
        else:
            args += pos
        r = herdr_run(None, *args, timeout=60)
        if r.returncode != 0:
            die("engine_fail", (r.stderr or r.stdout or "").strip()[:300], rc=1)
        out = (r.stdout or "").strip()
        if out:
            print(out)
        emit_ok({"status": "ok", "verb": verb})
        return

    die("usage", f"未知动词「{verb}」(view/status/add/rename/remove/enable/disable/reconnect)", rc=2)

