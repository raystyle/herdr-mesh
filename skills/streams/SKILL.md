---
name: streams
description: >-
  流消息原语:播报、留痕、交回执、房间消息与私信(append 落流、尾读取阅)。Use when
  往流交回执或广播、播报进展、留痕、发房间消息、私信、回放或续读历史消息、查流列表时;
  触发词 streams、流、回执、房间、广播、播报、留痕、私信、贴房间、写流、回放、续读。
---

# streams - evo 流域原语

| 动词 | 文法 | 何时用 |
| --- | --- | --- |
| view | `view [流名] [--from <seq>\|--resume] [-n N]` | 要查流列表或读流 |
| append | `append <流> <消息>` | 要落一条消息(自动带 host 前缀) |
| to | `to <id> <流> <消息> [--force]` | 要定向递流(先入流再知会对方) |

## 文法

- 裸调用 = view;全局旗标以 `streams --llms` 为准
- `--from` 与 `--resume` 同时给时,resume 覆盖 from
- 消息一行一事;append-only,更正 = 追加新行注明对象
- fleet 流 = 全舰队回执主频道
- 保留策略:room/ 与 dm/ 14 天;长留内容上 shares 键
- 交付取用行 = `streams view <流> -n 20`;拒投不写流,原文不保(见坑表)
- 文件走 shares;共享规则见 `../agents/SKILL.md`

## 示例

```bash
streams view fleet --from 0 -n 20
streams append fleet "批X 回执:发版位 abc1234"
streams to workbench-claude fleet "回执:批 X 完成"
```

## 坑

| 错 | 对 |
| --- | --- |
| 手写引擎裸追加 | 用 `streams append`,host 前缀自动带 |
| 定向递流被拒后找原文 | 拒投不写流不保原文,改走 `append` 或 `--force` 重发 |
| 默认尾读当全量 | 只见最近 100 行;全量 `--from 0` |
| 取阅后回写确认 | 取阅只尾读,不回写 |

## 接着读

- `../agents/references/collab.md`:消息礼仪与 ack 惯例,交回执或发私信时
