---
patterns: [机册, 机器, 节点, 舰队, pane 直透, runtime, runtimes, ark, 环境对齐, machines]
---

## machines 机册域操作指导

- 册表:`machines view`(裸调用同)/ `status [名]` 可达态;注册 `add <ssh-target> [--label <名>]`(herdr 自动装远端起 server);`rename/remove/enable/disable/reconnect` 管册
- 直透:`run <节点> <格> <命令...>`(格内跑命令)/ `close <节点> <格>`(直关格,agent 在跑先 agents close 优雅退)/ `pane <节点> <子面...>`(list/get/read/split 直透)
- 运行环境:`runtime [view|init|check|install|update|doctor|heal|config] [工具...]`,骑 ark;栈真源 = 仓根 runtimes.toml;`--machine <节点>` 跨机经 ssh,`--repo <远端仓路径>`
- `nodes` 旧名已淘汰(prim 3.12 四端全撤),一律写 machines
- 坑:远端路径用绝对形或加引号(`~` 被本地 shell 吸收);reconnect 需交互终端,非交互态用 `status <名>` 查可达;装环境走 runtime + ark 镜像道,不手搓 apt
- agent 消息走 agents;工位开格分屏走 desks
