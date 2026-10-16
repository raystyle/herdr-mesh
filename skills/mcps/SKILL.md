---
name: mcps
description: >-
  MCP 目标域原语:驱动任意 MCP server(view 健康、tools 面、call 调用、注册表管理)。
  Use when 要探测或操作 MCP 工作台、vmi-mcp 面板/命令、跨机 MCP 目标注册、
  spawn 桌面进程时;触发词 mcps、MCP、vmi-mcp、工作台、面板、目标机、
  tools/call、arg-json。
---

# mcps - MCP 目标域原语(第八原语,出站)

| 动词 | 文法 | 何时用 |
| --- | --- | --- |
| view | `view [目标]` | 要看在册目标表 + 每机健康;带名 = 单机详情 |
| tools | `tools <目标>` | 要列该目标全部 tools 面 |
| call | `call <目标> <tool> [--arg k=v]... [--arg-json k=<json>]...` | 要调任意 tool;k=v 平值、arg-json 嵌套(argv 数组等) |
| add | `add <名> --url <URL> [--note <注>]` | 要注册新 MCP 目标 |
| remove | `remove <名>` | 要注销目标 |

## 文法

- 裸调用 = view;全局旗标以 `mcps --llms` 为准
- 值一律字符串形透传(MCP 客户端串化宽容性);嵌套结构必走 `--arg-json k=<json>`
- 超时:`--timeout <s>` 覆盖;view/tools 默认 10s、call 120s,上限 600
- 注册表 `~/.config/mcps/targets.yaml`(名 -> url,`MCPS_REGISTRY` env 覆盖)
- 引擎 = mcp2cli 二进制(`MCPS_BIN` env 指路);短连会话,一次一命
- 无 DELIVER/门控(出站操作域);示例目标族 = vmi-mcp 工作台

## 示例

```bash
mcps view
mcps tools my-vm
mcps call my-vm shell --arg cmd=whoami --arg wait=true
mcps call my-vm spawn --arg exe=cmd --arg-json 'args=["/c","echo hi"]'
mcps add my-mcp --url http://10.0.0.5:9881/mcp
```

## 坑

| 错 | 对 |
| --- | --- |
| 嵌套值走 `--arg k=v` 平传(服务端报 expected a sequence) | 嵌套必走 `--arg-json k=<json>` |
| 以为 vmi-mcp 专属动词(shell/pane)是原语动词 | 它们是目标 server 的 tool,经 `call` 直达 |
| session_id=0 当异常 | linux 无会话概念恒 0,非异常 |

## 接着读

- `../agents/SKILL.md`:id 文法与信封协议总面
