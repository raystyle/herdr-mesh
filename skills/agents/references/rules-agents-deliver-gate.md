---
patterns: [门控, 拒投, deferred, 代记, status 四态, delivered, 送达判定, 强投]
---

## agents DELIVER 门控与状态信封指导

- 门控 v2 = TUI 实况尾窗检测(尾 12 行,四家判标族,缺省回落 claude):操作对话框即拒(信任屏/权限屏/模式选择),空 TUI 可投,busy 排队不拦,误拒优于误投;`--force` 跳门控强投
- status 四态:delivered(投出且 15s 内转 working)/ deferred(门控拒投已代记,exit 1 但 ok:true,判定看退出码与 status)/ engine_fail / not_found
- 代记落点:目标格 `room/deferred/<pane id>`(shell 旧流按收方名),补收两边看;拒投不丢件
- 审计道:room/force-audit 流留痕
