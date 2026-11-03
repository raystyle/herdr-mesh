"""prim 消息契约(pydantic 形)——DELIVER 信封字段行的单一真源

契约:CONTRACT.md 六(模板契约 v2:from/to/@handle 域段;ai-ccoe 真源位 plugins/CONTRACT.md,归档仓根)
人话行自由;字段行与取用行逐字稳定,机器可解析(parse 网关收旧拒)。
六域字段:shares=key/name;streams=stream;tasks=cwd;pipes/ports=addr;agents 自由文。
"""
from __future__ import annotations
import re
from typing import Literal, Optional

try:
    from pydantic import BaseModel, Field
    _HAS_PYDANTIC = True
except ImportError:  # pydantic 缺位时降级壳(字段行手写拼,校验退为正则)
    _HAS_PYDANTIC = False
    BaseModel = object  # type: ignore
    def Field(*a, **k):  # type: ignore
        return None

Domain = Literal["agents", "shares", "streams", "tasks", "pipes", "ports"]


class MsgEnvelope(BaseModel if _HAS_PYDANTIC else object):
    """DELIVER 消息信封:四段 = 人话行 / 字段行 / 取用行(/ 正文可选)。

    字段行 v2:from= 与 to= 恒在(@handle 兼容 IM 直觉);from 机器段 = local(同机)| 在册别名(跨机),真 hostname 不进路由;
    域字段随域(shares=key+name / streams=stream / tasks=cwd / pipes/ports=addr)。
    """
    if _HAS_PYDANTIC:
        domain: Domain
        src_host: str
        src_pane: str = ""
        dst: str
        dst_kind: str = ""
        key: Optional[str] = None
        name: Optional[str] = None
        stream: Optional[str] = None
        cwd: Optional[str] = None
        addr: Optional[str] = None
        v: int = 1
        body: str = ""
    else:
        def __init__(
            self,
            domain: Domain = "agents",
            src_host: str = "",
            src_pane: str = "",
            dst: str = "",
            dst_kind: str = "",
            key: Optional[str] = None,
            name: Optional[str] = None,
            stream: Optional[str] = None,
            cwd: Optional[str] = None,
            addr: Optional[str] = None,
            v: int = 1,
            body: str = "",
            **_kw,
        ):
            self.domain = domain
            self.src_host = src_host
            self.src_pane = src_pane
            self.dst = dst
            self.dst_kind = dst_kind
            self.key = key
            self.name = name
            self.stream = stream
            self.cwd = cwd
            self.addr = addr
            self.v = v
            self.body = body

    # ---------- 渲染 ----------

    def headline(self) -> str:
        """人话行(域前缀 + @收方 + 一句话)。"""
        h = f"@{self.dst} " if self.dst else ""
        w = self.body or self.action_default()
        return f"[{self.domain}] {h}{w}"

    def action_default(self) -> str:
        return {
            "agents": "sent you a message",
            "shares": f"shared file {self.name or ''} with you",
            "streams": f"appended to stream {self.stream}",
            "tasks": "set the persistent task for your project",
            "pipes": "opened a real-time pipe (send to me via this addr)",
            "ports": "opened a port mapping (tailcat forward to reach it)",
        }[self.domain]

    @property
    def from_field(self) -> str:
        return f"{self.src_host}:{self.src_pane}" if self.src_pane else self.src_host

    def fieldline(self) -> str:
        """字段行(逐字稳定,机器面)。"""
        parts = [f"from={self.from_field}", f"to={self.dst}"]
        if self.key:
            parts.append(f"key={self.key}")
        if self.name:
            parts.append(f"name={self.name}")
        if self.stream:
            parts.append(f"stream={self.stream}")
        if self.cwd:
            parts.append(f"cwd={self.cwd}")
        if self.addr:
            parts.append(f"addr={self.addr}")
        parts.append(f"v={self.v}")
        return " ".join(parts)

    def use_line(self, use_cmd: str) -> str:
        """取用行(use 行;2026-10-15 英文令:指令面全英文)。"""
        return f"use: {use_cmd}"

    def render(self, use_cmd: str) -> str:
        """完整信封,定稿形(2026-10-15 用户令三次定形):
        [域] @收方 <一句话正文>(头行,带全部路由面) / 空行 / 字段行 / use 行。
        结构行沉底(机器可解析面),正文自然段在头。"""
        head = f"[{self.domain}] @{self.dst} {self.body or self.action_default()}"
        return "\n".join([head, "", self.fieldline(), self.use_line(use_cmd)])


# ---------- 解析(收方机读) ----------

_FIELD = re.compile(r"(from|to|key|name|stream|cwd|addr|v)=(\S+)")


def parse_fieldline(line: str) -> dict:
    """字段行解析:from/to 恒须,域字段可选;缺 from/to 视为旧形(收方记 compatibility 警)。"""
    d = dict(_FIELD.findall(line))
    return d


def is_v2(line: str) -> bool:
    d = parse_fieldline(line)
    return "from" in d and "to" in d
