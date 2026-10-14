"""ctx 域(第六原语)- agent 对话历史检索(引擎 ClickHouse,gw_logs 库)

命令族: view(最近请求头行)/ show(单请求全链)/ search(跨请求全文)
数据面: lan-linux2 gwlogs 实例(https 8123 直连主道,双闸 = client 证书 + basic)。双道:
  1. 直连 https 8123(basic,ctx_reader SELECT-only;8123 mTLS 不收证书,密码道是正解)
  2. ssh 道兜底(容器内 client;无凭据或直连失败时自动落)
凭据: 环境变量 CTX_URL/CTX_USER/CTX_PASSWORD;缺省读 ~/.ctx/reader.env(600)
窗口: head 365 天(索引行),gwlog 180 天(正文块);TTL 由库面定,此处只读
"""
from __future__ import annotations
import json
import os
import ssl
import subprocess
import sys
import urllib.parse
import urllib.request

CRED_PATH = os.path.expanduser("~/.ctx/reader.env")


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


def _conf() -> dict:
    """配置面:环境变量优先,次读 ~/.ctx/reader.env(600;URL/USER/PASSWORD/CERT/KEY/CA)。"""
    keys = ("CTX_URL", "CTX_USER", "CTX_PASSWORD", "CTX_CERT", "CTX_KEY", "CTX_CA")
    conf = {k: os.environ.get(k, "") for k in keys}
    if os.path.isfile(CRED_PATH):
        for line in open(CRED_PATH, encoding="utf-8"):
            line = line.strip()
            for k in keys:
                if line.startswith(k + "=") and not conf[k]:
                    conf[k] = line.split("=", 1)[1]
    return conf


def _creds() -> tuple[str, str, str] | None:
    c = _conf()
    return (c["CTX_URL"], c["CTX_USER"], c["CTX_PASSWORD"]) if (c["CTX_URL"] and c["CTX_USER"] and c["CTX_PASSWORD"]) else None


def _http_ch(sql: str, timeout: int = 15) -> str:
    """直连 https 8123。双闸:client 证书(TLS 层,dctl CA;服务端要求)+ basic(用户层)。
    服务端证书名与地址不合,关主机名校验;有 CA 则校验链,无则裸 TLS(边界 = 网段 ACL)。"""
    conf = _conf()
    q = urllib.parse.quote(sql)
    req = urllib.request.Request(f"{conf['CTX_URL']}/?query={q}")
    import base64
    tok = base64.b64encode(f"{conf['CTX_USER']}:{conf['CTX_PASSWORD']}".encode()).decode()
    req.add_header("Authorization", f"Basic {tok}")
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    if conf["CTX_CA"]:
        ctx.load_verify_locations(os.path.expanduser(conf["CTX_CA"]))
    else:
        ctx.verify_mode = ssl.CERT_NONE
    if conf["CTX_CERT"] and conf["CTX_KEY"]:
        ctx.load_cert_chain(os.path.expanduser(conf["CTX_CERT"]), os.path.expanduser(conf["CTX_KEY"]))
    r = urllib.request.urlopen(req, timeout=timeout, context=ctx)
    return r.read().decode("utf-8", errors="replace")


def _ssh_ch(sql: str, timeout: int = 15) -> str:
    """ssh 道兜底:容器内 client(免本机证书面)。"""
    cmd = ("docker exec dctl-ch-gwlogs-26.8 clickhouse-client --secure --port 9440 "
           "--host 127.0.0.1 --config-file /etc/clickhouse-server/dctl/cli.xml "
           f"--query {json.dumps(sql, ensure_ascii=False)}")  # ensure_ascii=False:CJK 裸传
    try:
        r = subprocess.run(["ssh", "lan-linux2", cmd], capture_output=True, text=True,
                           timeout=timeout + 5, encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        _die("engine_fail", "查询超时(ssh 道到 lan-linux2)")
    if r.returncode != 0:
        _die("engine_fail", f"CH 查询失败:{(r.stderr or '').strip()[:150]}")
    return r.stdout or ""


def _ch(sql: str, timeout: int = 15) -> str:
    """主道直连,败落 ssh;两道皆败才报错(错误原文带出直连失败因)。"""
    if _creds():
        try:
            return _http_ch(sql, timeout)
        except Exception as e:
            e_msg = str(e)[:120]
            try:
                return _ssh_ch(sql, timeout)
            except SystemExit:
                raise
            # ssh 道 die 已带自身错误;此处不达
    return _ssh_ch(sql, timeout)


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
        print(_ch(sql))

    elif verb == "show":
        if not pos:
            _die("usage", "show <request_id>", "ctx view 找 request_id", rc=2)
        rid = _esc(pos[0])
        sql = (f"SELECT toString(ts), agent, alias, status, duration_ms, "
               f"input_tokens, output_tokens, thinking_tokens, session_id, error_summary "
               f"FROM gw_logs.head WHERE request_id = '{rid}' FORMAT TSVWithNames")
        out = _ch(sql)
        if len(out.strip().splitlines()) <= 1:  # TSVWithNames 零行仍出表头
            _die("not_found", "request_id 无记录(可能过 365 天窗口)", "ctx view 复核 id")
        print(out)
        sql2 = (f"SELECT seq, kind, substring(payload, 1, 4000) FROM gw_logs.gwlog "
                f"WHERE request_id = '{rid}' ORDER BY seq FORMAT TSV")
        body = _ch(sql2)
        if body.strip():
            print("-- 正文块(每块截 4000 字):")
            print(body)
        else:
            print("-- 正文块:空(可能过 180 天窗口)")

    elif verb == "search":
        kw = pos[0] if pos else ""
        if not kw:
            _die("usage", "search <关键词>", rc=2)
        # 检索面(全文索引裁定 2026-10-14):统一 multiSearchAnyUTF8 吃 idx_text
        # (text 索引 ngrams(2),ASCII/CJK/短语同道);needle < 2 字符无索引意义,拒
        if len(kw.encode("utf-8")) < 2:
            _die("usage", "关键词至少 2 个字符(UTF-8 计)", "短词换长词或 ctx view 浏览", rc=2)
        limit = _val("--limit", "10")
        sql = (f"SELECT request_id, count() AS hits, toString(min(ts)) AS t "
               f"FROM gw_logs.gwlog WHERE multiSearchAnyUTF8(payload, ['{_esc(kw)}']) "
               f"GROUP BY request_id ORDER BY t DESC LIMIT {limit} FORMAT TSVWithNames")
        out = _ch(sql)
        print(out if len(out.strip().splitlines()) > 1 else "(无命中;块表 180 天窗口)")

    else:
        _die("usage", f"未知动词「{verb}」;--llms 看手册", rc=2)
