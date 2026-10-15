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
except ImportError:  # pydantic 缺位时降级壳(字段行手写拼,校验退为正则)
    BaseModel = object  # type: ignore
    def Field(*a, **k):  # type: ignore
        return None

Domain = Literal["agents", "shares", "streams", "tasks", "pipes", "ports"]


class MsgEnvelope(BaseModel if isinstance(BaseModel, type) else object):
    """DELIVER 消息信封:四段 = 人话行 / 字段行 / 取用行(/ 正文可选)。

    字段行 v2:from= 与 to= 恒在(@handle 兼容 IM 直觉);from 机器段 = local(同机)| 在册别名(跨机),真 hostname 不进路由;
    域字段随域(shares=key+name / streams=stream / tasks=cwd / pipes/ports=addr)。
    """
    domain: Domain
    src_host: str                     # 发方机标签
    src_pane: str = ""                # 发方格(无名格空)
    dst: str                          # 收方 id(名或 机:格)
    dst_kind: str = ""                # 收方 agent 类(claude/codex/grok/kimi/pi)
    # 域字段
    key: Optional[str] = None         # shares
    name: Optional[str] = None        # shares 文件名
    stream: Optional[str] = None      # streams
    cwd: Optional[str] = None         # tasks
    addr: Optional[str] = None        # pipes/ports
    # 元
    v: int = 1                        # 信封版本
    body: str = ""                    # 人话行(正文)

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
