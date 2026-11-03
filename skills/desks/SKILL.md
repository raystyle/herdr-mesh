---
name: desks
description: >-
  工位与窗格拓扑原语:开工作台(仓即台)、起停格与分屏切tab、聚焦翻台、信任放行、拓扑真视图。
  Use when: open workbench, split pane, start agent, 工位、工作台、窗台、开台、开格、起格、
  分屏、切tab、关格、聚焦、翻台、信任屏、win 窗口视图、看拓扑、窗台工位分组视图。
  不要用于发消息与等回信(走 agents)或机册管理(走 machines)。
---

规则面已转 hook_rules(意图注入与路径注入);注入未发生时(非 Claude 端或 hook 缺位)直读 `plugins/evo/hook_rules/` 下同名与拆件。
