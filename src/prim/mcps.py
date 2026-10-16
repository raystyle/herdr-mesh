"""mcps 域:通用 MCP 客户端原语(第八原语,v3.5.0)

任意 MCP server 皆为目标(streamable-HTTP 形;stdio v2 再议);vmi-mcp 工作台
只是首批在册示例。骑 mcp2cli 二进制(Rust MCP 客户端,MCP 版本协商自适应),
不自写 MCP 客户端。评审裁定(2026-10-16 设计评审):add/remove 进首版;
--arg-json 逃生舱必收(spawn argv 嵌套实证);stdio 首版不收;view 退化形 =
initialize 成功即 alive。
"""
from __future__ import annotations
from . import core
import json
import os
import subprocess
import sys
from .core import die, emit_ok, eprint

# ---------- 注册表(~/.config/mcps/targets.yaml;win/WSL 各持家目录一份) ----------

def _registry_path() -> str:
    base = os.environ.get("MCPS_REGISTRY") or os.path.join(
        os.path.expanduser("~"), ".config", "mcps", "targets.yaml")
    return base

def _load_targets() -> dict:
    """读注册表 {名: {url, note}};缺文件 = 空(裸 view 出空表不炸)。"""
    p = _registry_path()
    if not os.path.isfile(p):
        return {}
    try:
        import yaml  # pyyaml 首版新依赖(注册表 yaml 形)
        d = yaml.safe_load(open(p, encoding="utf-8")) or {}
        return {k: v for k, v in d.items() if isinstance(v, dict) and v.get("url")}
    except Exception as e:
        die("engine_fail", f"注册表读败 {_registry_path()}: {e}", rc=1)

def _save_targets(t: dict) -> None:
    p = _registry_path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    import yaml
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        yaml.safe_dump(t, f, allow_unicode=True, sort_keys=True)

# ---------- mcp2cli 二进制解析(MCPS_BIN env > win 仓内 > PATH) ----------

def _mcp2cli() -> str:
    b = os.environ.get("MCPS_BIN")
    if b and os.path.isfile(b):
        return b
    from shutil import which
    w = which("mcp2cli")
    if w:
        return w
    die("engine_fail", "mcp2cli binary missing (set MCPS_BIN or install to PATH)", rc=1)

def _run(url: str, words: list[str], timeout: float) -> subprocess.CompletedProcess:
    """单次 MCP 会话(短连):mcp2cli --url <url> <words>。"""
    argv = [_mcp2cli(), "--url", url, *words]
    popen_kw: dict = {}
    if os.name != "nt":
        popen_kw["start_new_session"] = True
    try:
        proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, encoding="utf-8", errors="replace", **popen_kw)
    except OSError as e:
        return subprocess.CompletedProcess(argv, 125, "", f"mcp2cli spawn fail: {e}")
    try:
        out, err = proc.communicate(timeout=timeout)
        return subprocess.CompletedProcess(argv, proc.returncode, out or "", err or "")
    except subprocess.TimeoutExpired:
        core._kill_tree(proc)
        return subprocess.CompletedProcess(argv, 124, "", f"op_timeout: mcp2cli 超 {timeout:.0f}s")

# ---------- 健康探测(view) ----------

def _health(url: str, timeout: float) -> dict:
    """健康判据(评审裁定):initialize 成功即 alive;有 status tool 则并出摘要。"""
    r = _run(url, ["tool", "call", "status", "--output", "json"], timeout)
    if r.returncode != 0:
        # 退化形:server 可能无 status tool,initialize 面用 tool list 探
        r2 = _run(url, ["tool", "list"], timeout)
        return {"alive": r2.returncode == 0,
                "detail": (r2.stdout or r2.stderr or "")[:80].strip().replace("\n", " ")}
    try:
        d = json.loads(r.stdout)
        lines = d.get("lines") or []
        hb = next((l for l in lines if l.lstrip().startswith("{")), "")
        h = json.loads(hb) if hb else {}
        return {"alive": True, "pid": h.get("pid"), "user": h.get("user"),
                "panes": h.get("panes"), "uptime_s": h.get("uptime_s")}
    except Exception:
        return {"alive": True, "detail": (r.stdout or "")[:80].strip().replace("\n", " ")}

# ---------- 动词面 ----------

def mcps_view(target: str | None) -> None:
    ts = _load_targets()
    if not ts:
        eprint("mcps: 注册表空;add <名> --url <URL> 先注册(mcps --llms 看手册)")
    if target:
        t = ts.get(target) or die("not_found", f"目标「{target}」不在册",
                                  [{"command": "mcps view", "description": "查在册目标"}])
        h = _health(t["url"], _timeout(g_default=10))
        emit_ok({"status": "ok", "target": target, **t, "health": h})
        return
    print(f"{'TARGET':<14} {'URL':<42} HEALTH")
    for name, t in sorted(ts.items()):
        h = _health(t["url"], 10)
        mark = "alive" if h.get("alive") else "down"
        print(f"{name:<14} {t['url']:<42} {mark}" +
              (f" pid={h['pid']} user={h['user']} panes={h['panes']}" if h.get("alive") and h.get("pid") is not None else
               (f" {h.get('detail','')}" if h.get("detail") else "")))
    emit_ok({"status": "ok", "count": len(ts)})

def mcps_tools(target: str) -> None:
    ts = _load_targets()
    t = ts.get(target) or die("not_found", f"目标「{target}」不在册", rc=1)
    r = _run(t["url"], ["tool", "list"], _timeout(g_default=10))
    if r.returncode != 0:
        die("engine_fail", (r.stderr or r.stdout or "").strip()[:200], rc=1)
    # mcp2cli tool list 人读面:行 = "name  tool  description";--json 走全局旗标
    print(r.stdout.strip())

def mcps_call(target: str, tool: str, args: list[str]) -> None:
    """call <目标> <tool> [--arg k=v]... [--arg-json k=<json>]...
    值一律字符串形透传(MCP 客户端串化宽容性);--arg-json 原样 JSON 嵌套(评审裁定 2)。"""
    ts = _load_targets()
    t = ts.get(target) or die("not_found", f"目标「{target}」不在册", rc=1)
    words = ["tool", "call", tool]
    argv_args: list[str] = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--arg" and i + 1 < len(args):
            argv_args += ["--arg", args[i + 1]]
            i += 2
        elif a == "--arg-json" and i + 1 < len(args):
            k, _, v = args[i + 1].partition("=")
            try:
                json.loads(v)  # 形校验;原样透传 mcp2cli --arg-json(原生 JSON 值)
            except json.JSONDecodeError as e:
                die("usage", f"--arg-json 值非法 JSON: {e};期望形 k=<json>(如 --arg-json 'args=[\"/c\",\"echo hi\"]',键在前 JSON 在后)", rc=2)
            argv_args += ["--arg-json", args[i + 1]]
            i += 2
        else:
            die("usage", f"未知参数形「{a}」(call 只收 --arg k=v / --arg-json k=<json>)", rc=2)
    r = _run(t["url"], words + argv_args + ["--output", "json"], _timeout(g_default=120))
    if r.returncode == 124:
        die("op_timeout", r.stderr, rc=1)
    if r.returncode != 0:
        die("engine_fail", (r.stderr or r.stdout or "").strip()[:300], rc=1)
    try:
        d = json.loads(r.stdout)
        for line in d.get("lines") or []:
            print(line)
    except Exception:
        print(r.stdout.strip())
    emit_ok({"status": "ok", "target": target, "tool": tool})

def mcps_add(name: str, args: list[str]) -> None:
    if "--url" not in args:
        die("usage", "add <名> --url <URL> [--note <注>](stdio 首版不收,v2 再议)", rc=2)
    url = args[args.index("--url") + 1]
    note = args[args.index("--note") + 1] if "--note" in args else ""
    ts = _load_targets()
    ts[name] = {"url": url, "note": note}
    _save_targets(ts)
    print(f"mcps: 已注册 {name} -> {url}")
    emit_ok({"status": "ok", "target": name, "url": url})

def mcps_remove(name: str) -> None:
    ts = _load_targets()
    if name not in ts:
        die("not_found", f"目标「{name}」不在册", rc=1)
    del ts[name]
    _save_targets(ts)
    print(f"mcps: 已注销 {name}")
    emit_ok({"status": "ok", "removed": name})

def _timeout(g_default: float) -> float:
    """--timeout 旗标覆盖;上限 600(与 vmi-mcp wait 对齐)。"""
    for i, a in enumerate(sys.argv):
        if a == "--timeout" and i + 1 < len(sys.argv):
            try:
                return min(float(sys.argv[i + 1]), 600.0)
            except ValueError:
                pass
    return g_default

# ---------- 入口 ----------

def mcps_main():
    from .cli import parse, setup, handle_globals, manual
    g, verb, pos = parse(sys.argv[1:])
    setup("mcps", g)
    handle_globals(g, manual("mcps"))
    verb = verb or "view"
    if verb == "view":
        mcps_view(pos[0] if pos else None)
    elif verb == "tools":
        if not pos:
            die("usage", "tools <目标>", rc=2)
        mcps_tools(pos[0])
    elif verb == "call":
        if len(pos) < 2:
            die("usage", "call <目标> <tool> [--arg k=v] [--arg-json k=<json>]", rc=2)
        mcps_call(pos[0], pos[1], pos[2:])
    elif verb == "add":
        if not pos:
            die("usage", "add <名> --url <URL> [--note <注>]", rc=2)
        mcps_add(pos[0], pos[1:])
    elif verb == "remove":
        if not pos:
            die("usage", "remove <名>", rc=2)
        mcps_remove(pos[0])
    else:
        die("usage", f"未知动词「{verb}」(view/tools/call/add/remove)", rc=2)
