---
name: machines
description: >-
  机册原语:herdr machine 舰队节点管理(view/status/add/rename/remove/enable/disable/
  reconnect)、原始窗格直透(run/close/pane)、agent 运行环境面(runtime,骑 ark)。
  Use when: machine registry, run in a pane, runtime check, 查或管舰队机器与节点、
  在指定节点窗格跑命令或关窗格、检查或对齐某仓 agent 运行环境时;触发词 machines、
  机册、机器、节点、舰队节点、pane 直透、runtime、runtimes、ark、环境对齐。
  不要用于 agent 消息与等回信(走 agents)或工位开格分屏(走 desks)。
---

规则面已转 hook_rules(意图注入与路径注入);注入未发生时(非 Claude 端或 hook 缺位)直读 `plugins/evo/hook_rules/` 下同名与拆件。
