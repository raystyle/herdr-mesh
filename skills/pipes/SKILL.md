---
name: pipes
description: >-
  实时字节;close <addr> 停听。
  听侧 open,写侧 send。
  Use when: tail live stdout, stream bytes, 实时喂字节、日志尾随。
  不要用于跟房间消息。
---

规则面已转 hook_rules(意图注入与路径注入);注入未发生时(非 Claude 端或 hook 缺位)直读 `plugins/evo/hook_rules/` 下同名与拆件。
