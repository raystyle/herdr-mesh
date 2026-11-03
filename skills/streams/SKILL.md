---
name: streams
description: >-
  往房间或私信追加可回放的一行,回执与广播留痕;to = 先入流再叫人(留痕加知会一道,免 room 加 agents to 双发)。
  Use when: post a receipt, broadcast, dm, replay, send the stream and ping, 回执、群聊、私信、活跟随流。
  不要用于搬运文件本体。
---

规则面已转 hook_rules(意图注入与路径注入);注入未发生时(非 Claude 端或 hook 缺位)直读 `plugins/evo/hook_rules/` 下同名与拆件。
