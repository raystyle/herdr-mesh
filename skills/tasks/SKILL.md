---
name: tasks
description: >-
  持久任务原语:给别的格所在项目钉任务并定向委派,view 出各格现在跑什么的实时总览。
  Use when 设别的格的持久任务、跨机委派目标、查各格当前任务时(任务一道分野:一次性
  指令走 agents to,要对方记住的持久目标走本域);触发词 tasks、持久任务、记住任务、
  设任务、实时任务、钉任务、持久目标、在跑什么。
---

# tasks - evo 持久任务域原语

| 动词 | 文法 | 何时用 |
| --- | --- | --- |
| view | `view [机]` | 要 fleet 状态总览加本机各仓任务直读;远机任务用 `agents read <id>` 看屏 |
| set | `set <id> <文本>` | 要设目标格 cwd 的持久任务(只写不扰,知会走 to) |
| to | `to <id> <文本> [--force]` | 要定向委派(set 加知会) |

## 文法

- 裸调用 = view;全局旗标以 `tasks --llms` 为准
- 本地直设;远机零 ssh:pending 流加 apply 受体唤醒
- 任务键按格 agent 隔离:set/show 跟目标格 agent 类型(hst `--agent`),非 claude 格不断链
- 交付取用行 = `tasks view`;拒投自动代记(任务文本待设)
- 消息走 agents;共享规则见 `../agents/SKILL.md`

## 示例

```bash
tasks view lan-ubuntu
tasks set pve-harness-claude-1 "收束评审后发版"
tasks to pi-web "评审收束后发版" --json
```

## 坑

| 错 | 对 |
| --- | --- |
| 取用行写引擎裸命令(hst task show 等;goal 组 hst 2.15.0 已摘) | 执行信封上的 `tasks view` |
| 想知会对方却用 set | set 只写不扰;要对方知道用 to(set 加知会) |
| 目标格换目录后找不到任务 | 任务钉在设时的 cwd,以信封字段行 cwd 为准 |
| 目标机离线时等全表 | view 静默跳过不可达机不挂死(离线告警行在 agents 域) |

## 接着读

- `../agents/SKILL.md`:id 文法与委派信封,定向委派被拒时
