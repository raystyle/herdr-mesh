---
patterns: [MCP, mcps, vmi-mcp, 工作台, 面板, 目标机, tools/call, arg-json, mcp client]
---

## mcps 目标域操作指导

- 出站通用 MCP 客户端(骑 mcp2cli,无门控):`view` 健康、`tools` 工具面、`call` 调用、注册表 add/remove
- 调用形:`mcps call <目标> <工具> [--arg-json <JSON>]`;跨机 MCP 目标注册进册表后按名取用
- spawn 桌面进程(vmi-mcp 面板命令)同走本域
- 不要用于:agent 消息投递(走 agents)、本机窗格操作(走 desks/machines)
