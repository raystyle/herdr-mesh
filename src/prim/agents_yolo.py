"""agents yolo 子面:四家 CLI 的 yolo 检测与翻台(v3.7.0;用户令 2026-10-17)。

研究定谳(grok 研究单 yolo-detect-flip.txt,share c58479c604):
- 检测 = 状态栏/屏面正则(配置文件改模式时 argv 看不见);
- 热翻有限:claude bypass 须启动入环、kimi 斜杠要补 Enter、codex /permissions;
  可靠翻台 = 冷翻(写用户级配置 + /exit 退场 + fresh 起吃新配置);
- 各家全跳过值:claude bypassPermissions / codex never+danger-full-access /
  kimi auto(Never Ask;yolo 只是 Ask When Needed,仍会问!)/
  grok always-approve。
"""
from __future__ import annotations
from . import core
import json
import os
import subprocess
import sys
import time
from .core import die, emit_ok, eprint, herdr_run, _agents_of, _machine_labels

# 检测正则族(状态栏实读形;研究单判据表,按序首中即判)
MODE_PATTERNS: dict[str, list] = {
    "claude": [("bypass permissions on", True), ("auto mode on", False),
               ("accept edits on", False), ("plan mode on", False),
               ("manual mode on", False), ("don't ask on", False)],
    "codex": [("Full Access", True), ("Read Only", False), ("Workspace Write", False)],
    "kimi": [("Never Ask", True), ("Ask When Needed", False), ("Always Ask", False)],
    "grok": [("always-approve", True), ("plan", False), ("auto", False)],
}

# 用户级配置配方(研究单设置配方表;翻台只写用户级,项目级各家不生效)
CONFIG_RECIPES: dict[str, dict] = {
    "claude": {
        "path": "~/.claude/settings.json",
        "json": {"permissions": {"defaultMode": "bypassPermissions"},
                 "skipDangerousModePermissionPrompt": True},
    },
    "codex": {
        "path": "~/.codex/config.toml",
        "toml": {"approval_policy": "never", "sandbox_mode": "danger-full-access"},
    },
    "kimi": {
        "path": "~/.kimi-code/config.toml",
        "toml": {"default_permission_mode": "auto"},  # auto = Never Ask;yolo 仍会问
    },
    "grok": {
        "path": "~/.grok/config.toml",
        "toml": {"ui": {"permission_mode": "always-approve"}},
    },
}

CLI_CMD = {"claude": "claude", "codex": "codex", "kimi": "kimi", "grok": "grok"}
CFG_PATHS = {"claude": "~/.claude/settings.json", "codex": "~/.codex/config.toml",
             "kimi": "~/.kimi-code/config.toml", "grok": "~/.grok/config.toml"}


def detect(machine: str, pane: str, kind: str):
    """读屏判模式 -> (mode 显示串, yolo)。读不到 = (None, None)。"""
    m = None if machine in ("", "local") else machine
    r = herdr_run(m, "agent", "read", pane, "--lines", "25", timeout=30)
    visible = (r.stdout or "") + (r.stderr or "")
    for pat, is_yolo in MODE_PATTERNS.get(kind, []):
        if pat in visible:
            return pat, is_yolo
    return None, None


def _write_local_config(kind: str) -> str:
    """本机用户级配置写(幂等合并)。返回路径。"""
    path = os.path.expanduser(CFG_PATHS[kind])
    rec = CONFIG_RECIPES[kind]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if "json" in rec:
        data = {}
        if os.path.isfile(path):
            try:
                data = json.load(open(path, encoding="utf-8"))
            except Exception:
                data = {}

        def merge(dst, src):
            for k, v in src.items():
                if isinstance(v, dict) and isinstance(dst.get(k), dict):
                    merge(dst[k], v)
                else:
                    dst[k] = v
        merge(data, rec["json"])
        json.dump(data, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        return path
    # toml:追加/改键行(极简行形;键值单行,单层节)
    lines = open(path, encoding="utf-8").read().splitlines() if os.path.isfile(path) else []
    for key, val in rec["toml"].items():
        if isinstance(val, dict):
            sec, skey = key, list(val)[0]
            sval = val[skey]
            in_sec = False
            wrote = False
            for i, ln in enumerate(lines):
                t = ln.strip()
                if t == f"[{sec}]":
                    in_sec = True
                    continue
                if t.startswith("["):
                    if in_sec and not wrote:
                        lines.insert(i, f"{skey} = \"{sval}\"")
                        wrote = True
                    in_sec = False
                    continue
                if in_sec and t.startswith(skey):
                    lines[i] = f"{skey} = \"{sval}\""
                    wrote = True
            if not wrote:
                lines += ["", f"[{sec}]", f"{skey} = \"{sval}\""]
        else:
            hit = False
            for i, ln in enumerate(lines):
                if ln.strip().startswith(key):
                    lines[i] = f"{key} = \"{val}\""
                    hit = True
                    break
            if not hit:
                lines.append(f"{key} = \"{val}\"")
    open(path, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    return path


_REMOTE_WRITER = (
    "import json,os,sys\n"
    "k=sys.argv[1]\n"
    "paths={'claude':'~/.claude/settings.json','codex':'~/.codex/config.toml',"
    "'kimi':'~/.kimi-code/config.toml','grok':'~/.grok/config.toml'}\n"
    "p=os.path.expanduser(paths[k])\n"
    "os.makedirs(os.path.dirname(p),exist_ok=True)\n"
    "if k=='claude':\n"
    "    import json as j\n"
    "    d={}\n"
    "    try:\n"
    "        d=j.load(open(p)) if os.path.isfile(p) else {}\n"
    "    except Exception:\n"
    "        d={}\n"
    "    d.setdefault('permissions',{})['defaultMode']='bypassPermissions'\n"
    "    d['skipDangerousModePermissionPrompt']=True\n"
    "    j.dump(d,open(p,'w'),indent=2)\n"
    "elif k=='grok':\n"
    "    ls=open(p).read().splitlines() if os.path.isfile(p) else []\n"
    "    sec=False;wrote=False\n"
    "    for i,l in enumerate(ls):\n"
    "        t=l.strip()\n"
    "        if t=='[ui]':\n"
    "            sec=True;continue\n"
    "        if t.startswith('['):\n"
    "            if sec and not wrote:\n"
    "                ls.insert(i,'permission_mode = \"always-approve\"');wrote=True\n"
    "            sec=False;continue\n"
    "        if sec and t.startswith('permission_mode'):\n"
    "            ls[i]='permission_mode = \"always-approve\"';wrote=True\n"
    "    if not wrote:\n"
    "        ls+=['','[ui]','permission_mode = \"always-approve\"']\n"
    "    open(p,'w').write('\\n'.join(ls)+'\\n')\n"
    "else:\n"
    "    keys={'codex':[('approval_policy','never'),('sandbox_mode','danger-full-access')],"
    "'kimi':[('default_permission_mode','auto')]}[k]\n"
    "    ls=open(p).read().splitlines() if os.path.isfile(p) else []\n"
    "    for key,val in keys:\n"
    "        hit=False\n"
    "        for i,l in enumerate(ls):\n"
    "            if l.strip().startswith(key):\n"
    "                ls[i]=key+' = \"'+val+'\"';hit=True;break\n"
    "        if not hit:\n"
    "            ls.append(key+' = \"'+val+'\"')\n"
    "    open(p,'w').write('\\n'.join(ls)+'\\n')\n"
    "print(p)\n"
)


def _write_config(kind: str, machine):
    """写用户级 yolo 配置;远端经 ssh 家目录写。返回路径/错误说明。"""
    if machine and machine not in ("", "local"):
        import shlex
        # 机册 target 形(ray@host)直连:裸机名走 ssh config 默认用户会写错家(win 默认 root 的坑)
        from .runtimes import _machine_target
        target = _machine_target(machine)
        cmd = "python3 -c " + shlex.quote(_REMOTE_WRITER) + " " + shlex.quote(kind)
        r = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", target, cmd],
                           capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            return f"remote-write-fail: {(r.stderr or '')[:120]}"
        return r.stdout.strip() or "(remote)"
    return _write_local_config(kind)


def yolo_main(pos: list, g: dict) -> None:
    """agents yolo [--audit] | yolo <id> [--yes]:全舰队检测 / 单格冷翻。"""
    from .cli import resolve
    yes = "--yes" in sys.argv
    pos = [a for a in pos if not a.startswith("-")]

    if not pos:
        # 全舰队检测面(local + 各在册机)
        rows = []
        scopes = [("local", "")]
        for lab in _machine_labels():
            scopes.append((lab, lab))
        for host, m in scopes:
            try:
                ags = _agents_of(m or None, timeout=15)
            except Exception:
                continue
            for a in ags:
                kind = a.get("agent") or ""
                if kind not in MODE_PATTERNS:
                    continue
                mode, is_yolo = detect(m, a.get("pane_id", ""), kind)
                rows.append({"machine": host, "pane": a.get("pane_id"),
                             "kind": kind, "cwd": a.get("cwd"),
                             "mode": mode, "yolo": is_yolo})
        if g.get("json"):
            emit_ok({"status": "ok", "count": len(rows), "rows": rows})
            return
        print(f"{'HOST':<12} {'PANE':<9} {'KIND':<7} {'MODE':<24} YOLO")
        needy = []
        for r in rows:
            mark = {True: "yes", False: "NO"}.get(r["yolo"], "?")
            print(f"{r['machine']:<12} {r['pane']:<9} {r['kind']:<7} {str(r['mode']):<24} {mark}")
            if r["yolo"] is False:
                needy.append(f"{r['machine']}:{r['pane']}({r['kind']})")
        if needy:
            print(f"\n非 yolo {len(needy)} 格;治:agents yolo <id> --yes(冷翻:用户级配置+/exit+fresh 起)")
            eprint("非 yolo: " + ", ".join(needy))
        else:
            print("\n全绿(? = 屏面无模式串,不可判)")
        return

    # 单格翻台(冷翻三步:写配置 -> 退场 -> fresh 起)
    m, pane = resolve(pos[0])
    agents = _agents_of(None if m in ("", "local") else m)
    me = next((a for a in agents if a.get("pane_id") == pane), None)
    kind = (me or {}).get("agent") or ""
    if kind not in CONFIG_RECIPES:
        die("usage", f"「{kind or '?'}」不在四家面(claude/codex/kimi/grok)", rc=2)
    before_mode, before_yolo = detect(m, pane, kind)
    if before_yolo:
        print(f"agents: 已是 yolo({before_mode}),无需翻")
        emit_ok({"status": "ok", "target": f"{m}:{pane}", "kind": kind,
                 "before": before_mode, "after": before_mode, "executed": False})
        return
    if not yes:
        print(f"plan: {kind} 冷翻 @ {m}:{pane}")
        print(f"  1) 写用户级 {CFG_PATHS[kind]}(全跳过值;研究单配方)")
        print("  2) /exit 退场(冷翻 = 新进程吃新配置;会话上下文不迁)")
        print("  3) fresh 起 CLI")
        print("  默认预览未执行;加 --yes 执行本次变更")
        emit_ok({"status": "planned", "target": f"{m}:{pane}", "kind": kind, "before": before_mode})
        return
    hm = None if m in ("", "local") else m
    wrote = _write_config(kind, m)
    herdr_run(hm, "agent", "prompt", pane, "/exit", "--wait", "--until", "working", "--timeout", "15000", timeout=45)
    for _ in range(12):
        time.sleep(1.5)
        r = herdr_run(hm, "agent", "get", pane, timeout=10)
        if r.returncode != 0:
            break
    herdr_run(hm, "pane", "run", pane, CLI_CMD[kind], timeout=30)
    after_mode, after_yolo = None, None
    for _ in range(15):
        time.sleep(2.5)
        after_mode, after_yolo = detect(m, pane, kind)
        if after_yolo:
            break
    print(f"yolo 翻 {m}:{pane}({kind}):{before_mode} -> {after_mode}"
          + ("  OK" if after_yolo else "  仍非 yolo(查托管/requirements 锁)"))
    emit_ok({"status": "ok", "target": f"{m}:{pane}", "kind": kind,
             "before": before_mode, "after": after_mode, "executed": True,
             "ok": after_yolo is True, "config": wrote})
