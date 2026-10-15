---
name: shares
description: >-
  交付或取回一份已写完的文件。
  Use when: send the file, attach, fetch a share key, 传文件、取文件。
  不要用于还在长的字节或只发一条消息。
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
- 交付取用行 = `agents to <别名> reply`;键在字段行 key=,拒投自动代记,文件已在键上不丢件
- 流消息走 streams;共享规则(id、门控、信封)见 `../agents/SKILL.md`

## 示例

```bash
shares view
shares put report.md
shares get <put 打印的键>
shares to ai-ccoe-claude-1 report.md --json
```

## 坑

| 错 | 对 |
| --- | --- |
| 在取用行里找键 | 键在字段行 key=;取文件用 `shares get <键>` |
| 大内容直接进流 | 先 put 上键,流里只放键引用 |
| 发版只传键 | 键与 sha 两写并存:键 = 取用面,sha = 验证面 |
| 取回不落名撞本地件 | 用 `-o` 指定落名 |

## 接着读

- `../agents/SKILL.md`:id 文法与投递信封,定向交付被拒时
