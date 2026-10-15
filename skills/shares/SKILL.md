---
name: shares
description: >-
  文件共享原语:把文件交给指定 agent 或全舰队(上架回键、取回、定向交付;拒投时文件
  已在键上,不丢件)。Use when 传文件给某 agent、给某格递文件、交付文件、取回
  别人共享的文件、大内容上键流里放引用时;触发词 shares、共享、给文件、传文件、递文件、
  交付、取回、上架、传给某格。
---

# shares - evo 文件域原语

| 动词 | 文法 | 何时用 |
| --- | --- | --- |
| view | `view` | 要看 share/ 键表 |
| put | `put <文件>` | 要上架文件换键 |
| get | `get <键> [-o\|--output 名]` | 要取回文件(缺省存键尾文件名) |
| to | `to <id> <文件> [--force]` | 要把文件定向交付给某 agent(上架加知会) |

## 文法

- 裸调用 = view;全局旗标以 `shares --llms` 为准
- 键形 `share/<源机>/<内容短哈希>/<文件名>`;同内容同键,不同内容不互覆
- 交付取用行 = `shares get <键>`;拒投自动代记,文件已在键上不丢件
- 流消息走 streams;共享规则(id、门控、信封)见 `../agents/SKILL.md`

## 示例

```bash
shares view
shares put report.md
shares get <刚打印的键>
shares to workbench-claude-1 report.md --json
```

## 坑

| 错 | 对 |
| --- | --- |
| 大内容直接进流 | 先 put 上键,流里只放键引用 |
| 发版只传键 | 键与 sha 两写并存:键 = 取用面,sha = 验证面 |
| 取回不落名撞本地件 | 用 `-o` 指定落名 |

## 接着读

- `../agents/SKILL.md`:id 文法与投递信封,定向交付被拒时
