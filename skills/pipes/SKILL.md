---
name: pipes
description: >-
  实时字节原语:让对方持续往我这里发字节(日志尾随、进度流)。Use when 开实时管道、
  要对方实时发日志或进度、看本机活动管道、跨机看管道在册时;触发词 pipes、管道、实时发、
  实时流、日志尾随、字节、进度、对方发日志。
---

# pipes - evo 实时字节域原语

| 动词 | 文法 | 何时用 |
| --- | --- | --- |
| view | `view [host]` | 要看本机活动管道;带机 = 跨机只读(公开行) |
| open | `open` | 要本机起收听(回地址与日志位) |
| close | `close <addr\|pid>` | 要关管道,地址作废 |
| send | `send <addr>` | 要连对方管道发数据(stdin 直通;recipient 侧动词) |
| to | `to <id> [--force]` | 要开管道并知会对方 |

## 文法

- 裸调用 = view;全局旗标以 `pipes --llms` 为准
- 字节方向恒 = 本机收、对方发
- 与 ports 分野:本域 = 临时字节管道(stdio 直连);TCP 端口转发映射走 ports
- 管道常驻至 close,无超时自关(`--keep` 已废,rc=2 拒)
- 取用行 = `pipes send <addr>`(send 已落 v3.4.3,引擎名退出取用行)
- 地址与日志落 `~/.local/state/pipe/`
- 消息走 agents;跨机只读走 room/pipe-live 流;共享规则见 `../agents/SKILL.md`

## 示例

```bash
pipes view lan-ubuntu
pipes open --keep
pipes close <addr>
pipes to evo-claude
```

## 坑

| 错 | 对 |
| --- | --- |
| 想让对方收你的字节而自己 open | 方向不可换:对方 open、你被 to |
| 用完不关占听位 | 用毕 `close`;对端重连前先 close 旧地址 |
| win 首用直连被拦 | win 防火墙默认入站 Block;命令自带 CTA 放行提醒,规则名 tailcat-in(仅 DERP 中继可达即此因) |

## 接着读

- `../agents/SKILL.md`:id 文法与知会信封,管道知会被拒时
