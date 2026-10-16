---
name: tasks
description: >-
  钉一条跨回合还在的任务。
  set 只写不扰,to 加知会。
  Use when: pin a task, keep doing, what is running, 钉住、记住、一直做、在跑什么。
  不要用于一句过了就没用的指令。
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
tasks view node-a
tasks set pve-harness-claude-1 "收束评审后发版"
tasks to web-agent-1 "评审收束后发版" --json
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
