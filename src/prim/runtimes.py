"""nodes 域 runtime 子面:agent 运行时环境检查与管理(挂在 nodes 下,不立新原语;用户令 2026-10-17)。

骑 ark(Agent Runtime Kit)为引擎。栈真源 = 仓根 runtimes.toml(由工作台仓的
agent 自己定);本面对照 ark 三态(locked/installed/path)做检查与管理,
天然跨机(nodes 机册节点经 ssh 直跑远端 ark)。config 面 v1 只读。
"""
from __future__ import annotations
from . import core
import json
import os
import subprocess
import sys
from .core import die, emit_ok, eprint
from .nodes import _machines_raw

MANIFEST = "runtimes.toml"  # 仓根环境需求清单(仓 agent 自定)

TEMPLATE = """# runtimes.toml - 本仓工作台环境需求(仓 agent 自定,本文件 = 真源)
# 工具名对齐 ark catalog(nodes runtime --machine <节点> 看);version 可省(跟 ark pin 锁)
[tools]
# claude = ""      # 例:四家 CLI
# git = ""
# uv = ""
"""


def _ark_bin(machine: str | None = None) -> str:
    """ark 调用前缀:本机直跑 or 远端 ssh 包(节点经 nodes 机册寻址)。"""
    b = os.environ.get("ARK_BIN")
    if b and os.path.isfile(b):
        return b
    from shutil import which
    w = which("ark")
    if w:
        return w
    die("engine_fail", "ark 二进制缺位(ARK_BIN env 指路,或 ark init 自举)", rc=1)


def _machine_target(label: str) -> str:
    for m in _machines_raw():
        if m.get("label") == label:
            return m.get("target") or label
    die("not_found", f"节点「{label}」不在机册(nodes view 查)", rc=1)


def _sh_quote(s: str) -> str:
    """单引号包安全形(内单引号转义);ssh 远端命令串用。"""
    return "'" + s.replace("'", "'\''") + "'"


def _ssh_run(target: str, argv: list[str], timeout: float, login: bool = False) -> subprocess.CompletedProcess:
    # login 形:包 bash -lc 走 ~/.profile(~/.local/bin 等 PATH 增量;非交互 ssh 不吃 .bashrc)
    cmd = 'bash -lc ' + _sh_quote(" ".join(argv)) if login else " ".join(argv)
    full = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", target, cmd]
    try:
        return subprocess.run(full, capture_output=True, text=True, timeout=timeout,
                              encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(full, 124, "", f"op_timeout: ssh 超 {timeout:.0f}s")


def _ark_run(args: list[str], timeout: float = 120, machine: str | None = None) -> subprocess.CompletedProcess:
    if machine:
        # 远端恒用 PATH 上的 ark(本地 win 路径不可执于远端;ARK_BIN 只管本机)
        # login shell:ssh 非交互不吃 .bashrc,~/.local/bin 进不来
        return _ssh_run(_machine_target(machine), ["ark", *args], timeout, login=True)
    argv = [_ark_bin(), *args]
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                              encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(argv, 124, "", f"op_timeout: ark 超 {timeout:.0f}s")


def _ark_status_map(machine: str | None = None) -> dict[str, dict]:
    r = _ark_run(["status", "--json"], machine=machine)
    if r.returncode != 0:
        die("engine_fail", (r.stderr or r.stdout or "").strip()[:250], rc=1)
    try:
        d = json.loads(r.stdout)
        if isinstance(d, dict):
            d = d.get("data", {}).get("data") if isinstance(d.get("data"), dict) and "data" in d["data"] else d.get("data")
        return {t["tool"]: t for t in (d or []) if isinstance(t, dict)}
    except json.JSONDecodeError:
        return {}


def _parse_tools_block(text: str) -> dict[str, str]:
    """清单 [tools] 解析,兼容两形(2026-10-17 实战形对齐):
    平形:[tools] 段内 `名 = "版本"`;富形:`[tools.名]` 子表,取其 version 键
    (channel/purpose 等注记键忽略)。"""
    out: dict[str, str] = {}
    section = ""  # ""=不在 tools;"tools"=平形;"tools.<名>"=富形子表
    for line in text.splitlines():
        t = line.strip()
        if t.startswith("[") and t.endswith("]"):
            sec = t[1:-1].strip()
            if sec == "tools":
                section = "tools"
            elif sec.startswith("tools."):
                section = sec
                out.setdefault(sec[len("tools."):], "")
            else:
                section = ""
            continue
        if not section or "=" not in t or t.startswith("#"):
            continue
        k, _, v = t.partition("=")
        k = k.strip()
        v = v.strip().strip(chr(34)).strip(chr(39))
        if section == "tools":
            out[k] = v
        elif section.startswith("tools.") and k == "version":
            out[section[len("tools."):]] = v
    return out


def _load_manifest(machine: str | None = None, repo: str | None = None) -> dict[str, str]:
    """仓根 runtimes.toml -> {工具: 版本约束};远端形经 ssh cat(--repo 指远端仓路径)。"""
    if machine:
        rp = repo or "~"
        # 本地 ~ 被调用方 shell 展开成本机家目录时,归一回远端家(bash 未加引号常见坑)
        lh = os.path.expanduser("~").replace("\\", "/")
        if lh and rp.startswith(lh):
            rp = "~" + rp[len(lh):]
        r = _ssh_run(_machine_target(machine), ["cat " + rp + "/" + MANIFEST + " 2>/dev/null"], 20)
        if r.returncode != 0 or not r.stdout.strip():
            return {}
        return _parse_tools_block(r.stdout)
    p = os.path.join(os.getcwd(), MANIFEST)
    if not os.path.isfile(p):
        return {}
    try:
        import tomllib
        with open(p, "rb") as f:
            d = tomllib.load(f)
        tools = d.get("tools", {})
        if not isinstance(tools, dict):
            return {}
        flat = {}
        for k, v in tools.items():
            if isinstance(v, dict):
                flat[str(k)] = str(v.get("version", "") or "")
            else:
                flat[str(k)] = str(v or "")
        return flat
    except ImportError:
        return _parse_tools_block(open(p, encoding="utf-8").read())
    except Exception as e:
        die("engine_fail", f"{MANIFEST} 读败: {e}", rc=1)


def _manifest_status(machine: str | None = None, repo: str | None = None) -> list[dict]:
    man = _load_manifest(machine=machine, repo=repo)
    st = _ark_status_map(machine=machine)
    rows = []
    for tool, want in man.items():
        t = st.get(tool)
        if not t:
            rows.append({"tool": tool, "want": want or "-", "locked": "-",
                         "installed": "-", "path": "?", "state": "not-in-catalog"})
            continue
        gap = not t.get("installed")
        drift = bool(t.get("locked") and t.get("installed") and t["locked"] != t["installed"]) or not t.get("path")
        pin_bad = bool(want and t.get("installed") and not str(t["installed"]).startswith(want))
        state = "gap" if gap else ("pin-mismatch" if pin_bad else ("drift" if drift else "ok"))
        rows.append({"tool": tool, "want": want or "-", "locked": t.get("locked") or "-",
                     "installed": t.get("installed") or "-", "path": "yes" if t.get("path") else "NO",
                     "state": state})
    return rows


def _flag_value(flag: str):
    for i, a in enumerate(sys.argv):
        if a == flag and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
        if a.startswith(flag + "="):
            return a.split("=", 1)[1]
    return None


def _config_check(machine: str | None = None) -> dict:
    """agent 配置面只读检查:CLI 配置目录在位 + 网关 env(远端经 ssh test)。"""
    checks = {
        "claude-config": "~/.claude",
        "codex-config": "~/.codex",
        "herdr-config": "~/.config/herdr",
        "gateway-env": "$ANTHROPIC_BASE_URL",
    }
    items = {}
    for k, p in checks.items():
        if machine:
            r = _ssh_run(_machine_target(machine), [f"test -e {p} && echo y || echo n"], 15)
            items[k] = (r.stdout or "").strip().endswith("y")
        else:
            items[k] = os.path.exists(os.path.expanduser(p))
    missing = [k for k, v in items.items() if not v]
    return {"ok": not missing, "items": items, "note": f"缺 {', '.join(missing)}" if missing else ""}


def runtime_main(pos: list[str], g: dict) -> None:
    """nodes runtime [子动词] [工具...];裸 = view。--machine <节点> --repo <远端仓路径>。"""
    machine = _flag_value("--machine")
    repo = _flag_value("--repo")
    # 从位置参里剥掉旗标对(--machine X / --repo X / 裸 --yes),免被当子动词
    stripped: list[str] = []
    skip_next = False
    for a in pos:
        if skip_next:
            skip_next = False
            continue
        if a in ("--machine", "--repo"):
            skip_next = True
            continue
        if a.startswith("--machine=") or a.startswith("--repo=") or a == "--yes" or a.startswith("-"):
            continue
        stripped.append(a)
    sub = stripped[0] if stripped else "view"
    rest = stripped[1:]

    if sub in ("view", "status"):
        man = _load_manifest(machine=machine, repo=repo)
        if not man:
            where = machine or "本机"
            eprint(f"nodes runtime: {where} 无 {MANIFEST}(栈由仓 agent 自定;本机 nodes runtime init 出模板)")
            emit_ok({"status": "ok", "machine": machine or "local", "count": 0,
                     "hint": f"nodes runtime init -> 编辑 {MANIFEST}"})
            return
        rows = _manifest_status(machine=machine, repo=repo)
        if rest:
            rows = [r for r in rows if r["tool"] == rest[0]] or die(
                "not_found", f"「{rest[0]}」不在清单({MANIFEST})", rc=1)
        if g.get("json"):
            emit_ok({"status": "ok", "machine": machine or "local", "count": len(rows), "tools": rows})
            return
        print(f"{'TOOL':<12} {'WANT':<10} {'LOCKED':<12} {'INSTALLED':<12} PATH  STATE  @{machine or 'local'}")
        for r in rows:
            print(f"{r['tool']:<12} {r['want']:<10} {r['locked']:<12} {r['installed']:<12} {r['path']:<5} {r['state']}")
        bad = sum(1 for r in rows if r["state"] != "ok")
        print(f"\n清单 {len(rows)} 工具,异常 {bad}(对齐: nodes runtime update;详诊: nodes runtime doctor)")
        return

    if sub == "init":
        if machine:
            die("usage", "init 只出本机模板(远端清单由远端仓 agent 自建)", rc=2)
        p = os.path.join(os.getcwd(), MANIFEST)
        if os.path.isfile(p):
            die("usage", f"{MANIFEST} 已在(勿重复建;直接编辑)", rc=2)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(TEMPLATE)
        print(f"nodes runtime: 模板已出 {p}(agent 按本仓需求编辑 [tools])")
        emit_ok({"status": "ok", "created": MANIFEST})
        return

    if sub == "check":
        man = _load_manifest(machine=machine, repo=repo)
        if not man:
            die("usage", f"{'节点 ' + machine if machine else '本机'}无 {MANIFEST};先 init 并按需编辑", rc=2)
        rows = _manifest_status(machine=machine, repo=repo)
        bad = [r for r in rows if r["state"] != "ok"]
        cfg = _config_check(machine=machine)
        ok = not bad and cfg.get("ok")
        if g.get("json"):
            emit_ok({"status": "ok" if ok else "degraded", "machine": machine or "local",
                     "tools": rows, "config": cfg})
        else:
            for r in rows:
                print(f"  {r['state']:<13} {r['tool']:<10} want={r['want']} installed={r['installed']} path={r['path']}")
            for k, v in cfg.get("items", {}).items():
                print(f"  {'cfg-ok' if v else 'cfg-MISS':<13} {k}")
        sys.exit(0 if ok else 1)

    if sub in ("install", "update"):
        man = _load_manifest(machine=machine, repo=repo)
        if not man:
            die("usage", f"{'节点 ' + machine if machine else '本机'}无 {MANIFEST};栈由仓自定,先 init+编辑", rc=2)
        tools = rest if rest else list(man)
        unknown = [t for t in tools if t not in man]
        if unknown:
            die("usage", f"工具不在清单: {', '.join(unknown)}(清单外的走 ark 直令)", rc=2)
        if "--yes" not in sys.argv:
            print(f"plan: ark {sub} {' '.join(tools)}" + (f" @ {machine}" if machine else ""))
            print("  默认预览未执行;加 --yes 执行本次变更")
            emit_ok({"status": "planned", "verb": sub, "machine": machine or "local", "tools": tools})
            return
        r = _ark_run([sub, *tools], timeout=600, machine=machine)
        if r.returncode != 0:
            die("engine_fail", (r.stderr or r.stdout or "").strip()[:300], rc=1)
        out = (r.stdout or "").strip()
        if out:
            print(out[-2000:])
        emit_ok({"status": "ok", "verb": sub, "machine": machine or "local", "tools": tools})
        return

    if sub in ("doctor", "heal"):
        if sub == "heal" and "--yes" not in sys.argv:
            print(f"plan: ark heal {' '.join(rest) or '(全量)'}" + (f" @ {machine}" if machine else ""))
            print("  默认预览未执行;加 --yes 执行自愈")
            emit_ok({"status": "planned", "verb": "heal"})
            return
        r = _ark_run([sub, *rest], timeout=300, machine=machine)
        print((r.stdout or "").strip()[-2000:])
        if r.returncode != 0:
            eprint((r.stderr or "").strip()[:300])
        sys.exit(r.returncode)

    if sub == "config":
        cfg = _config_check(machine=machine)
        if g.get("json"):
            emit_ok({"status": "ok" if cfg.get("ok") else "degraded", "machine": machine or "local", **cfg})
            return
        for k, v in cfg.get("items", {}).items():
            print(f"  {'ok ' if v else 'MISS'} {k}")
        print(f"配置面: {'ok' if cfg.get('ok') else 'degraded'} {cfg.get('note', '')}")
        sys.exit(0 if cfg.get("ok") else 1)

    die("usage", f"未知子动词「{sub}」(view/status/init/check/install/update/doctor/heal/config)", rc=2)
