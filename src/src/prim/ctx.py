"""ctx 域(第六原语)- agent 对话历史检索(引擎 ClickHouse,gw_logs 库)

命令族: view(最近请求头行)/ show(单请求全链)/ search(跨请求全文)
数据面: ClickHouse gw_logs 库;查询经 ssh 道到存储节点,容器内 client 执行
(TLS 证书不落本机);连接由环境变量配置(CTX_HOST/CTX_CONTAINER),公开仓不内置节点名
窗口: head 365 天(索引行),gwlog 180 天(正文块);TTL 由库面定,此处只读
"""
from __future__ import annotations
import json
import os
import subprocess
import sys

CTX_HOST = os.environ.get("CTX_HOST", "")              # 存储节点 ssh 别名
CTX_CONTAINER = os.environ.get("CTX_CONTAINER", "")    # clickhouse 容器名
CTX_CLIENT_ARGS = os.environ.get("CTX_CLIENT_ARGS", "--secure")  # client 连接参(如证书配置)


def _die(code: str, msg: str, cta=None, rc: int = 1):
    from . import core
    if core.JSON_MODE:
        err = {"code": code, "message": msg, "cta": [cta] if cta else []}
        print(json.dumps(err, ensure_ascii=False), file=sys.stderr)
    else:
        print(f"ctx: {msg}", file=sys.stderr)
        if cta:
            print(f"下一步:{cta}", file=sys.stderr)
    sys.exit(rc)


def _ssh_ch(sql: str, timeout: int = 15) -> str:
    """经 ssh 到存储节点容器内 client 执行(免本机证书面;TLS 证书不落本机)。"""
    if not CTX_HOST or not CTX_CONTAINER:
        _die("engine_fail", "未配存储节点(CTX_HOST/CTX_CONTAINER 环境变量)",
             "export CTX_HOST=<ssh 别名> CTX_CONTAINER=<容器名>")
    cmd = (f"docker exec {CTX_CONTAINER} clickhouse-client {CTX_CLIENT_ARGS} "
           f"--query {json.dumps(sql)}")
    try:
        r = subprocess.run(["ssh", CTX_HOST, cmd], capture_output=True, text=True,
                           timeout=timeout + 5, encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        _die("engine_fail", f"查询超时(ssh 道到 {CTX_HOST})")
    if r.returncode != 0:
        _die("engine_fail", f"CH 查询失败:{(r.stderr or '').strip()[:150]}")
    return r.stdout or ""


def _esc(s: str) -> str:
    """单引号转义(注入护栏;参数只进字面量位)。"""
    return s.replace("\\", "\\\\").replace("'", "\\'")


def ctx_main():
    from .cli import parse, setup, handle_globals, manual
    g, verb, pos = parse(sys.argv[1:])
    setup("ctx", g)
    handle_globals(g, manual("ctx"))
    verb = verb or "view"

    def _val(flag, default=""):
        if flag in pos and pos.index(flag) + 1 < len(pos):
            return pos[pos.index(flag) + 1]
        return default

    if verb == "view":
        agent = pos[0] if pos and not pos[0].startswith("-") else ""
        limit = _val("--limit", "20")
        where = f"WHERE agent = '{_esc(agent)}'" if agent else ""
        sql = (f"SELECT toString(ts) AS t, agent, alias, status, duration_ms, "
               f"input_tokens+cache_read+cache_creation AS in_tok, "
               f"output_tokens+thinking_tokens AS out_tok, request_id "
               f"FROM gw_logs.head {where} ORDER BY ts DESC LIMIT {limit} FORMAT TSVWithNames")
        print(_ssh_ch(sql))

    elif verb == "show":
        if not pos:
            _die("usage", "show <request_id>", "ctx view 找 request_id", rc=2)
        rid = _esc(pos[0])
        sql = (f"SELECT toString(ts), agent, alias, status, duration_ms, "
               f"input_tokens, output_tokens, thinking_tokens, session_id, error_summary "
               f"FROM gw_logs.head WHERE request_id = '{rid}' FORMAT TSVWithNames")
        out = _ssh_ch(sql)
        if len(out.strip().splitlines()) <= 1:  # TSVWithNames 零行仍出表头
            _die("not_found", "request_id 无记录(可能过 365 天窗口)", "ctx view 复核 id")
        print(out)
        sql2 = (f"SELECT seq, kind, substring(payload, 1, 4000) FROM gw_logs.gwlog "
                f"WHERE request_id = '{rid}' ORDER BY seq FORMAT TSV")
        body = _ssh_ch(sql2)
        if body.strip():
            print("-- 正文块(每块截 4000 字):")
            print(body)
        else:
            print("-- 正文块:空(可能过 180 天窗口)")

    elif verb == "search":
        kw = pos[0] if pos else ""
        if not kw:
            _die("usage", "search <关键词>", rc=2)
        limit = _val("--limit", "10")
        sql = (f"SELECT DISTINCT request_id, toString(min(ts)) AS t "
               f"FROM gw_logs.gwlog WHERE hasToken(payload, '{_esc(kw)}') "
               f"GROUP BY request_id ORDER BY t DESC LIMIT {limit} FORMAT TSVWithNames")
        out = _ssh_ch(sql)
        print(out if len(out.strip().splitlines()) > 1 else "(无命中;块表 180 天窗口)")

    else:
        _die("usage", f"未知动词「{verb}」;--llms 看手册", rc=2)
