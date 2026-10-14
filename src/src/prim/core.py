"""prim - 五原语共享核心(v3 python 形)

契约:ai-ccoe plugins/CONTRACT.md(五d 参数规范为本文法蓝图)
- 全局七旗标任意槽;-- 逃生口;未知词 usage 退 2
- id 三产生式:无冒号全局名 / 机:余段 / 裸 pane id = usage
- 投递动词统一 to;--force 投递专属任意槽
- 隐式路由:local 与 --machine 由 resolve 自适,调用方零感知
- status 四态:delivered|engine_fail|deferred|stalled
"""
from __future__ import annotations
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from dataclasses import dataclass

# ---------- 基础 ----------

def eprint(*a):
    print(*a, file=sys.stderr)

def emit_error(code: str, message: str, cta: list[dict] | None = None):
    """错误分道:stderr 单行 JSON(doc-cli 形);人读形前缀。退出码由调用方定。"""
    obj = {"code": code, "message": message}
    if cta:
        obj["cta"] = cta
    eprint(f"{CMD_NAME}: {message}" if not JSON_MODE else json.dumps(obj, ensure_ascii=False))

def emit_ok(data: dict):
    """成功信封:--json 时 stdout 单行 {ok,data,meta};人读形由调用方打印。"""
    if JSON_MODE:
        print(json.dumps({"ok": True, "data": data, "meta": {"command": CMD_NAME}}, ensure_ascii=False))

def die(code: str, message: str, cta: list[dict] | None = None, rc: int = 1):
    emit_error(code, message, cta)
    sys.exit(rc)

# ---------- 全局态(每命令入口重置) ----------

CMD_NAME = "agents"
JSON_MODE = False
FORCE = False

# ---------- 引擎定位 ----------

def _find_bin(name: str) -> str | None:
    p = shutil.which(name)
    if p:
        return p
    for c in (os.path.join(os.path.expanduser("~/.local/bin"), name),
              f"/usr/local/bin/{name}"):
        if os.path.exists(c):
            return c
    return None

def herdr() -> str:
    b = _find_bin("herdr")
    if not b:
        die("engine_fail", "本机无 herdr 二进制", rc=1)
    return b

def s5() -> str:
    b = _find_bin("s5")
    if not b:
        die("engine_fail", "本机无 s5 二进制(share/stream 引擎)", rc=1)
    return b

# s5 调用前缀:win 无本地 s5 时走 wsl 代役(wsl -e 直 exec,stdin/stdout 管道直通)
_S5_PREFIX: list[str] | None = None

def s5_cmd() -> list[str]:
    global _S5_PREFIX
    if _S5_PREFIX is None:
        b = _find_bin("s5")
        if b:
            _S5_PREFIX = [b]
        elif os.name == "nt":
            wsl_s5 = _wsl_exec() + ["/home/ray/.local/bin/s5"]
            try:
                r = subprocess.run(wsl_s5 + ["streams"], capture_output=True, text=True,
                                   timeout=10, encoding="utf-8", errors="replace")
                _S5_PREFIX = wsl_s5 if r.returncode == 0 else []
            except Exception:
                _S5_PREFIX = []
        else:
            _S5_PREFIX = []
    if not _S5_PREFIX:
        die("engine_fail", "本机无 s5 二进制(share/stream 引擎)", rc=1)
    return _S5_PREFIX

def _wsl_exec() -> list[str]:
    w = shutil.which("wsl.exe") or r"C:\Windows\System32\wsl.exe"
    return [w, "-e"]

def wsl_path(p: str) -> str:
    """win 路径转 wsl 形(D:\\x → /mnt/d/x);已在 wsl 形或 POSIX 形则原样。"""
    p = p.replace("\\", "/")
    if len(p) >= 2 and p[1] == ":":
        return f"/mnt/{p[0].lower()}{p[2:]}"
    return p

def host_path(p: str) -> str:
    """wsl /mnt/x 形转 win 形(供 get -o 输出落回本机);非该形原样。"""
    if p.startswith("/mnt/") and len(p) > 6 and p[5].isalpha() and p[6] == "/":
        return f"{p[5].upper()}:{p[6:]}"
    return p

def host_label() -> str:
    """本机名:优先 PRIM_HOST_LABEL(hostname 与机册注册名不合时设,如 win);
    缺省 hostname 短名(linux/mac 机hostname 即注册名)。"""
    env = os.environ.get("PRIM_HOST_LABEL")
    if env:
        return env
    return socket.gethostname().split(".")[0]

# ---------- herdr 调用(隐式路由核心) ----------

def herdr_run(machine: str | None, *args: str, timeout: int = 30) -> subprocess.CompletedProcess:
    """machine 为 None/local = 本机;否则 --machine 路由。引擎错误原文保留。
    容错(用户令 2026-10-14:离线机不挂死整面):超时/异常回 CompletedProcess(rc=124)不抛;
    KeyboardInterrupt 透传(用户 Ctrl+C 即退)。"""
    hb = herdr()
    cmd = [hb]
    if machine and machine != "local":
        cmd += ["--machine", machine]
    cmd += list(args)
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                              encoding="utf-8", errors="replace")
    except KeyboardInterrupt:
        raise
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, 124, "",
                                           f"herdr timeout after {timeout}s (machine={machine or 'local'})")
    except OSError as e:
        return subprocess.CompletedProcess(cmd, 125, "", f"herdr spawn fail: {e}")

def herdr_json(machine: str | None, *args: str) -> list | dict:
    r = herdr_run(machine, *args)
    if r.returncode != 0 or not r.stdout.strip():
        return []
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return []

# ---------- id 解析(三产生式) ----------

@dataclass
class Target:
    machine: str  # "" = 本机
    rest: str      # 名或格

def resolve(id_str: str) -> tuple[str, str]:
    """id 三产生式 → (machine, pane_or_name);解析失败 die not_found。"""
    if ":" in id_str:
        m, rest = id_str.split(":", 1)
        # 机标签合法性(在册或 local)
        if m == "local":
            return "local", rest
        labels = [x.get("label", "") for x in herdr_json(None, "machine", "list", "--json") if isinstance(x, dict)]
        if m in labels:
            return m, rest
        die("not_found", f"机器「{m}」不在册", [{"command": "agents machines", "description": "列在网机器"}])
    # 无冒号:全局按名搜(本机先,后各在册机)
    hit = _find_by_name("", id_str)
    if hit:
        return hit
    for lab in _machine_labels():
        hit = _find_by_name(lab, id_str)
        if hit:
            return hit
    die("not_found", f"全局未找到 agent「{id_str}」", [{"command": "agents view", "description": "查全局格表"}])

def _machine_labels() -> list[str]:
    out = []
    for x in herdr_json(None, "machine", "list", "--json"):
        if isinstance(x, dict) and x.get("enabled", True):
            out.append(x.get("label", ""))
    return [l for l in out if l and l != "local"]

def _agents_of(machine: str) -> list[dict]:
    d = herdr_json(machine or None, "agent", "list")
    if isinstance(d, dict):
        return d.get("result", {}).get("agents", []) or []
    return d if isinstance(d, list) else []

def _find_by_name(machine: str, name: str) -> tuple[str, str] | None:
    """machine ""=本机;命中名或 pane_id → (machine or "local", pane_id)。多名命中 = not_found(研究裁定)。"""
    ags = _agents_of(machine or None)
    hits = [a for a in ags if a.get("name") == name or a.get("pane_id") == name]
    if len(hits) > 1:
        die("not_found", f"「{name}」多名命中({len(hits)} 格)", [{"command": "agents view", "description": "查全局格表"}])
    if hits:
        return (machine or "local"), hits[0].get("pane_id", "")
    return None

def pane_cwd(machine: str, pane: str) -> str:
    for a in _agents_of(None if machine in ("", "local") else machine):
        if a.get("pane_id") == pane:
            return a.get("cwd") or os.path.expanduser("~")
    return os.path.expanduser("~")

# ---------- 门控与投递 ----------

def target_status(machine: str, pane: str) -> str:
    for a in _agents_of(None if machine in ("", "local") else machine):
        if a.get("pane_id") == pane:
            return a.get("agent_status", "unknown")
    return "unknown"

def deliver_prompt(machine: str, pane: str, text: str) -> str:
    """原子化投递:--wait --until working 15s。返回 status 四态之一。"""
    m = None if machine in ("", "local") else machine
    r = herdr_run(m, "agent", "prompt", pane, text, "--wait", "--until", "working", "--timeout", "15000", timeout=25)
    if r.returncode == 0:
        return "delivered"
    err = (r.stderr or r.stdout or "").strip()
    if "agent_blocked" in err:
        return "deferred"
    if "timeout" in err or "stalled" in err:
        return "stalled"
    return "engine_fail"

# 四家 TUI 操作对话框判标族(实测文案;保守清单,误拒优于误投)
TUI_DIALOGS: dict[str, tuple[str, ...]] = {
    "claude": (
        "Yes, I trust this folder", "Do you trust the files in this folder",
        "Yes, allow external imports", "Enter to confirm", "Esc to cancel",
        "Do you want to proceed", "don't ask again", "permission mode",
        "Select an option", "requires approval",
    ),
    "codex": (
        "Trust this folder?", "Do you trust the contents of this directory",
        "waiting for input", "Approve", "Run command", "select an option",
    ),
    "grok": (
        "Trust the authors of this folder", "Approve?", "Y/n",
        "press y to", "Enter to confirm",
    ),
    "kimi": (
        "Trust this folder", "Don't trust", "approve", "选择", "确认",
    ),
}

def gate(machine: str, pane: str) -> str | None:
    """投递门控 v2(用户令 2026-10-13:不看状态字段,看 TUI 实况,四家 TUI 判标族):
    读格可见内容,有操作对话框(信任屏/权限屏/模式选择)即拒;输入框空着即可投
    (busy 态各家 TUI 会排队消息,不是拒投理由)。返回 None = 可投。"""
    if FORCE:
        return None
    m = None if machine in ("", "local") else machine
    kind = ""
    for a in _agents_of(m):
        if a.get("pane_id") == pane:
            kind = a.get("agent") or ""
            break
    r = herdr_run(m, "agent", "read", pane, "--source", "visible", "--lines", "40", timeout=15)
    screen = r.stdout or ""
    # 只扫 TUI 尾窗(对话框按钮与页脚区):正文里的文档引用(如信任屏教学文)不算屏上对话框
    tail = "\n".join(screen.splitlines()[-12:])
    markers = TUI_DIALOGS.get(kind, ()) + TUI_DIALOGS.get("claude", ())
    hit = next((mk for mk in markers if mk in tail), None)
    if hit:
        return f"dialog({hit[:24]})"
    return None
