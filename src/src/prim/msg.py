"""prim 消息契约(pydantic 形)——DELIVER 信封字段行的单一真源

契约:ai-ccoe plugins/CONTRACT.md 六(模板契约 v2:from/to/@handle 域段)
人话行自由;字段行与取用行逐字稳定,机器可解析(parse 网关收旧拒)。
三域字段:shares=key/name;streams=stream;agents 自由文。
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

Domain = Literal["agents", "shares", "streams"]


class MsgEnvelope(BaseModel if isinstance(BaseModel, type) else object):
    """DELIVER 消息信封:四段 = 人话行 / 字段行 / 取用行(/ 正文可选)。

    字段行 v2(用户令 2026-10-13):from= 与 to= 恒在,@handle 兼容 IM 直觉;
    域字段随域(shares=key+name / streams=stream)。
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
            "agents": "给你递了一条消息",
            "shares": f"给你共享了文件「{self.name or ''}」",
            "streams": f"向流「{self.stream}」写入一行",
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
        parts.append(f"v={self.v}")
        return " ".join(parts)

    def use_line(self, use_cmd: str) -> str:
        """取用行。"""
        return f"取用:{use_cmd}"

    def render(self, use_cmd: str) -> str:
        """完整三行形(人话/字段/取用)。"""
        return "\n".join([self.headline(), self.fieldline(), self.use_line(use_cmd)])


# ---------- 解析(收方机读) ----------

_FIELD = re.compile(r"(from|to|key|name|stream|v)=(\S+)")


def parse_fieldline(line: str) -> dict:
    """字段行解析:from/to 恒须,域字段可选;缺 from/to 视为旧形(收方记 compatibility 警)。"""
    d = dict(_FIELD.findall(line))
    return d


def is_v2(line: str) -> bool:
    d = parse_fieldline(line)
    return "from" in d and "to" in d
