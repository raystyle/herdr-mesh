---
name: ports
description: >-
  暴露本机口用 open,访问对方已开的口用 fwd;close 停映射。
  Use when: expose a port, port-forward, 端口转发、映射服务口。
  不要用于文件或消息。
---

规则面已转 hook_rules(意图注入与路径注入);注入未发生时(非 Claude 端或 hook 缺位)直读 `plugins/evo/hook_rules/` 下同名与拆件。
