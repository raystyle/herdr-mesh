---
name: agents
description: >-
  消息域原语与六原语共享面:告诉或委派 agent 干活、读屏等回话、按键、在场声明、工位
  管理、查机器(项目协作规则文件不属本面)。Use when 委派某格干活、找格读屏、发消息或
  按键、查在场、开工作台调窗格布局、翻台重载、查在网机器时;触发词 agents、找格、读屏、
  窗格、工作台、关格、分屏、信任、勿扰、翻台、派单、门控、命名标准、presence、machines。
---

# agents - evo 消息域原语与六原语共享面

| 动词 | 文法 | 何时用 |
| --- | --- | --- |
| view | `view [机]`(族:`machines` 机表、`list [机]` 机读形) | 要全局格表与机册 |
| read | `read <id> [--lines N] [--timeout S]` | 要读某格屏幕或等队友回话(忙则内候) |
| to | `to <id> <文本> [--force]`(prompt 为别名) | 要给某格发一句话指令 |
| keys | `keys <id> <键>` | 要给某格按键(仅本机与 local: 目标) |
| start | `start <名> --kind <类> [--pane 格] [--cwd DIR] [--machine 机]` | 要起一个带名新格(非标形拒 rc=2;起名全局扫,撞名拒 rc=2) |
| close | `close <id>` | 要关格(优雅退后 shell exit,零击杀) |

## 文法

- 裸调用 = view;全局旗标任意槽,以 `agents --llms` 为准
- 投递动词统一 `to`;`--force` 任意参数位,跳门控强投
- id 三产生式:`<名>`(全局寻址,本机先) / `<机>:<名或格>` / `local:<格>`;裸 pane id 非法;投递与回信用裸别名,格 id 只用于窗格操作
- 命名标准:`<台名>-<类型>-<编号>`,字母开头禁下划线;编号 = 出生序号,该台该类型不复用(田字只约束创建顺序,非格位)
- 投递判成败:先退出码(0/1/2),再看 `--json` 的 `data.status`(delivered/engine_fail/deferred/stalled)与 CTA;拒投时信封仍 ok:true
- 门控只拒操作对话框(信任屏/权限屏/模式选择)
- 工位与在场族动词(ws、shell、dev、split、tab、zoom、wt、trust、sync、reload、mode)见 `references/workspace.md`
- 文件走 shares,流走 streams,持久任务走 tasks,实时字节走 pipes,历史对话走 ctx;共享细语义见本 skill references

## 示例

```bash
agents view
agents read workbench-claude --lines 40 --timeout 30
agents to workbench-claude "评审请求已递" --json
agents keys local:w13:p1 Enter
agents start hst-kimi-2 --kind kimi --cwd ~/repos/workbench-claude-1
agents close local:w13:p1
agents ws evo
agents tab list
```

## 坑

| 错 | 对 |
| --- | --- |
| 裸格直写格 id(如 `to w8:p1`) | 无名格用 `local:<格>` 或 `<机>:<格>` |
| 目标 working 就不敢投 | busy 排队不拦,照投;等回话用 `read` 忙候 |
| 判成败单看信封 ok 字段 | 先看退出码,再看 `data.status` |
| 装更插件后不翻台 | `reload <id>` 翻台才生效(旧进程 = 旧技能);回滚裸形时上下文弃,信封 resume 字段披露 |
| 同 cwd 多格投递按格猜发话方 | caller_addr 歧义不猜,退化机名加告警;按名寻址 |
| grok 面信封见单行拍扁 | 收方 TUI 显示怪癖,定稿四行形不降协议(见 deliver-gate 信封节) |

## 接着读

- `references/addressing.md`:id 解析算法、命名标准细则、from 核验,跨机寻址出错时
- `references/deliver-gate.md`:门控判据、status 四态、信封 v2 定稿四行形、代记补收,投递被拒或读信封时
- `references/collab.md`:IM 映射、回执与 ack 惯例、回放与保留策略,交回执或发房间消息时
