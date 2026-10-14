# agent mesh 架构

## 分层

```
显示层   Windows Terminal / herdr TUI(哑面,只管布局与呈现;wt 只开窗无读写)
物理层   herdr(workspace > tab > pane;agent 生命周期检测 idle/working/blocked/done)
执行层   CLI agent(claude / codex / grok / kimi / pi,TUI 会话)
协议层   五原语命令(本仓 src/)+ 消息契约(MsgEnvelope)
引擎层   s5(S3 对象 + S2 流)/ hst(持久任务)/ tailcat(实时管道)
```

控制面与显示面分离: 程序化控制全走协议层命令,终端窗口只是给人看。已开终端标签无读写道,控制落在会话内的 herdr API 上。

## 端点形态

| 端点 | herdr | 特点 |
| --- | --- |
| win | 本机 server + PRIM_HOST_LABEL 覆盖 | s5 缺位走 WSL 代役(路径互转) |
| linux | 本机 server | /usr/local/bin 安装位需提权滚版 |
| mac | 本机 server,ssh LAN 直达 | tailscale ssh 客户端缺口,LAN 互注册 |
| pi(NAT 后) | systemd 持久 server | 远端走尾网段端点 |

机册: 各端 herdr machine list 互注册;herdr --machine 转发面(api 族 + workspace/pane 族,session/attach 不可转)。

## 寻址

- 裸名: 全局按 agent 名搜(本机先,后在册机逐台);多名命中 = not_found
- 机:名或格: 首冒号前 = 机标签(在册或 local),余段整段 = 名或格
- 裸 pane id 非法(含冒号先当机标签解析)

命名标准: 工作台标签-agent类型-编号(编号 = 田字顺时针窗格位,满四开 tab 续增);存量名兼容。

## 投递语义

投递动词统一 to。链路 = 门控(TUI 尾窗判对话框)到原子化写入(herdr agent prompt --wait --until working 15s)。

status 四态:

| 状态 | 义 |
| --- | --- |
| delivered | 已投出且目标 agent 开吃 |
| engine_fail | 引擎写败,stderr 原文不吞 |
| deferred | 门控拒投,已代记 room/deferred/<格> |
| stalled | 写入但 15s 未开吃 |

退出码 0/1/2(成功/失败/用法错);拒投时信封 ok 字段仍 true(ok = 命令执行无误,status = 投递态,分轨)。

## 消息信封 v2

```
[<域>] @<收方> <一句话动作>          人话行(自由)
from=<host>:<pane> to=<id> <域字段> v=1   字段行(逐字稳定,机器可解析)
取用:<可复制命令行>                   取用行(禁改写)
```

域字段: shares=key/name,streams=stream,tasks=cwd,pipes=addr;agents 自由文。
pydantic 契约(src/prim/msg.py)是单一真源,收方 parse_fieldline 机读,旧形记兼容警。

## 翻台(技能重载)

agent 进程不热载技能;reload 动词 = 优雅退场(/exit 会话持久化)后同格同 session 重进(--continue 族)。idle 门: 非 idle 拒翻,--force 过。

## 网关日志(伴生面)

网关全量请求细节入 ClickHouse 头表(90 天)+ 正文块表(14 天),按 req_id/session 两步检索回溯;细节见 ai-ccoe operations/templates/vector-gateway(私仓)。
