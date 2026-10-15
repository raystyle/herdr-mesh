---
name: ctxs
description: >-
  对话历史检索原语:查任何 agent 跑过的请求(最近请求头行、单请求原文、跨请求全文搜词)。
  Use when 查历史对话、回溯对话细节、按 request_id 调单次请求原文、跨请求搜关键词、看某
  agent 最近请求开销时;触发词 ctx、历史对话、对话历史、request_id、上次请求、历史请求、
  请求开销、原文。
---

# ctx - evo 对话历史域原语

| 动词 | 文法 | 何时用 |
| --- | --- | --- |
| view | `view [agent] [--limit N]` | 要最近请求的头行(时间/模型/token/耗时/request_id) |
| show | `show <request_id> [--around <词>] [--window N]` | 要单请求原文;`--around` 只看命中块±N 邻块 |
| search | `search <词> [--term <词>]... [--limit N]` | 跨请求全文搜词,多词 OR,行带 snip 片段 |

## 文法

- 裸调用 = view;词至少 2 字符(UTF-8 计)
- 窗口:head 365 天,正文 180 天
- 实时屏用 agents read,本命令只查历史

## 示例

```bash
ctxs view claude --limit 5
ctxs show 0192a0f0-xxxx --around "挂死" --window 1
ctxs search "panic"
ctxs search --term 杀树 --term ensure_ascii
```

## 坑

| 错 | 对 |
| --- | --- |
| show 之前不先取 request_id | 先 `ctxs view` 或 `ctxs search --limit 1`;view 的 request_id 在末列,search 的 request_id 在首列 |
| show 报「头行:未落」当 not_found | 头行未落正文已在属正常降级,接着读正文块;双无记录才 not_found |
| 表空当链路断 | 零行但表头出即链路通,数据候采集入库 |

## 接着读

- `ctx --llms`:旗标与窗口全集,要细旗标或默认值时
