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


def ctxs_main():
    from .cli import parse, setup, handle_globals, manual
    g, verb, pos = parse(sys.argv[1:])
    setup("ctxs", g)
    handle_globals(g, manual("ctxs"))
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
            _die("usage", "show <request_id> [--around <关键词>] [--window N]", "ctx view 找 request_id", rc=2)
        rid = _esc(pos[0])
        around = _val("--around", "")
        window = int(_val("--window", "1") or 1)
        sql = (f"SELECT toString(ts), agent, alias, status, duration_ms, "
               f"input_tokens, output_tokens, thinking_tokens, session_id, error_summary "
               f"FROM gw_logs.head WHERE request_id = '{rid}' FORMAT TSVWithNames")
        out = _ch(sql)
        sql2 = (f"SELECT seq, kind, substring(payload, 1, 4000) FROM gw_logs.gwlog "
                f"WHERE request_id = '{rid}' ORDER BY seq FORMAT TSV")
        body = _ch(sql2)
        # 管道时序(批150 实证):正文块先入,head 行随 request_end 后入;在途请求只有块
        if len(out.strip().splitlines()) <= 1 and not body.strip():
            _die("not_found", "request_id 无记录(可能过 365 天窗口)", "ctx view 复核 id")
        if len(out.strip().splitlines()) <= 1:
            print("-- 头行:未落(request 在途或 request_end 批未刷;正文块先行如下)")
        else:
            print(out)
        if not body.strip():
            print("-- 正文块:空(可能过 180 天窗口)")
        elif around:
            # 命中块 +/- window 邻块;匹配在 SQL 侧全文做(块可超 4000 字截断面)
            # 命中块正文改命中点居中窗口(先例 ctx show --window 形)
            if len(around.encode("utf-8")) < 2:
                _die("usage", "--around 关键词至少 2 个字符", rc=2)
            a = _esc(around)
            pos_chain = f"nullif(positionUTF8(payload, '{a}'), 0)"
            sql3 = (f"SELECT seq, substring(payload, greatest({pos_chain} - 120, 1), 3000) "
                    f"FROM gw_logs.gwlog WHERE request_id = '{rid}' "
                    f"AND multiSearchAnyUTF8(payload, ['{a}']) ORDER BY seq FORMAT TSV")
            hit_rows = _ch(sql3)
            if not hit_rows.strip():
                print(f"-- 正文块:无「{around}」命中块(查别的词或不带 --around 看全量)")
            else:
                hit = {int(r.split("\t", 1)[0]): r.split("\t", 1)[1]
                       for r in hit_rows.splitlines() if r.strip()}
                keep = set()
                for s in hit:
                    keep.update(range(s - window, s + window + 1))
                rows = body.splitlines()
                blocks = [(int(r.split("\t", 1)[0]), r) for r in rows if r.strip()]
                print(f"-- 正文块(命中 {sorted(hit)} ±{window};命中块为命中点居中 3000 字):")
                out_rows = []
                for s, r in blocks:
                    if s not in keep:
                        continue
                    if s in hit:
                        head = r.split("\t", 1)[0] + "\t"
                        out_rows.append(f"{head}«命中点»\t{hit[s]}")
                    else:
                        out_rows.append(r)
                print("\n".join(out_rows))
        else:
            print("-- 正文块(每块截 4000 字):")
            print(body)

    elif verb == "search":
        # 词集 = 位置参数 + --term 可叠(OR 语义,先例 ctx search --term 形)
        terms = []
        if pos and not pos[0].startswith("-"):
            terms.append(pos[0])
        i = 0
        while i < len(pos):
            if pos[i] == "--term" and i + 1 < len(pos):
                terms.append(pos[i + 1])
            i += 1
        if not terms:
            _die("usage", "search <关键词> [--term <词>]...", rc=2)
        # 检索面(全文索引裁定 2026-10-14):multiSearchAnyUTF8 吃 idx_text
        # (text 索引 ngrams(2),ASCII/CJK/短语同道);needle < 2 字符无索引意义,拒
        for t in terms:
            if len(t.encode("utf-8")) < 2:
                _die("usage", "关键词至少 2 个字符(UTF-8 计)", "短词换长词或 ctx view 浏览", rc=2)
        limit = _val("--limit", "10")
        esc = [_esc(t) for t in terms]
        arr = "[" + ",".join(f"'{t}'" for t in esc) + "]"
        cond = f"multiSearchAnyUTF8(payload, {arr})"
        # 片段:最早命中块内,首个出现词的位置开 120 字窗口(token 高效,先例 snippet 形)
        pos_chain = "coalesce(" + ",".join(
            f"nullif(positionUTF8(argMinIf(payload, ts, {cond}), '{t}'), 0)" for t in esc) + ", 0)"
        sql = (f"SELECT request_id, count() AS hits, toString(min(ts)) AS t, "
               f"substring(argMinIf(payload, ts, {cond}), greatest({pos_chain} - 40, 1), 120) AS snip "
               f"FROM gw_logs.gwlog WHERE {cond} "
               f"GROUP BY request_id ORDER BY t DESC LIMIT {limit} FORMAT TSVWithNames")
        out = _ch(sql)
        print(out if len(out.strip().splitlines()) > 1 else "(无命中;块表 180 天窗口)")

    else:
        _die("usage", f"未知动词「{verb}」;--llms 看手册", rc=2)
