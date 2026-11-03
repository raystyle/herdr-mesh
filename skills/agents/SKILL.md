---
name: agents
description: >-
  给格发指令并事件等回信(to/wait/inbox)、读屏按键、在场与翻台管理。
  Use when: tell, ask, ping, reply, read the screen, wait for a reply, 等回话、读屏、按键、
  派单、私信回执、翻台、在场声明。
  不要用于文件、房间留痕、跨回合任务或工位开格分屏(开格分屏走 desks)。
---

规则面已转 hook_rules(意图注入与路径注入);注入未发生时(非 Claude 端或 hook 缺位)直读 `plugins/evo/hook_rules/` 下同名与拆件。
