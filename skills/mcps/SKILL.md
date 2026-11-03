---
name: mcps
description: >-
  MCP 目标域原语:驱动任意 MCP server(view 健康、tools 面、call 调用、注册表管理)。
  Use when: MCP client, call a tool, list MCP tools, 探测或操作 MCP 工作台、跨机 MCP
  目标注册、vmi-mcp 面板命令、spawn 桌面进程时;触发词 mcps、MCP、vmi-mcp、工作台、
  面板、目标机、tools/call、arg-json。
  不要用于 agent 消息投递与本机窗格操作(走 agents)。
---

规则面已转 hook_rules(意图注入与路径注入);注入未发生时(非 Claude 端或 hook 缺位)直读 `plugins/evo/hook_rules/` 下同名与拆件。
