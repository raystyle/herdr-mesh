---
name: ports
description: >-
  端口映射原语:任意节点端口转发映射(端口表、定点映射、all、exit-node),对方
  tailcat forward 接入。Use when 开端口转发、把远端端口映射出来、看在册端口映射、
  让对方接入我的端口服务时;触发词 ports、端口、端口转发、端口映射、forward、
  转发、映射、exit-node、tailcat serve、tailcat forward。
---

# ports - evo 端口域原语

| 动词 | 文法 | 何时用 |
| --- | --- | --- |
| view | `view [机]` | 要看本机活动映射;带机 = 跨机公开行(room/port-live,机名用注册标签) |
| open | `open <spec> [--keep]` | 要起端口转发;spec = `8080,8443` 端口表 / `5555:IP:5555` 映射 / `all` / `exit-node` |
| close | `close <addr\|pid>` | 要关映射,地址作废 |
| to | `to <id> <spec> [--force]` | 要开映射并知会对方接入(取用行 tailcat forward) |

## 文法

- 裸调用 = view;全局旗标以 `ports --llms` 为准
- 与 pipes 分野:pipes = 临时字节管道(本机收对方发);本域 = TCP 端口转发映射(tailcat serve,对方 forward 接入)
- 取用行 = `tailcat forward <addr> [0:]<端口>`;addr 在字段行;多端口 spec 取用行只带首端口,其余照形自补
- 状态目录 `~/.local/state/ports`(pid/addr/log/spec 四件);跨机公开流 room/port-live(不含地址)
- 消息走 agents;共享规则见 `../agents/SKILL.md`

## 示例

```bash
ports view lan-ubuntu
ports open 8123
ports open 5555:10.2.200.213:5555
ports to evo-claude 8123
```

## 坑

| 错 | 对 |
| --- | --- |
| spec 敲成 URL 或带协议形 | 裸形:端口表逗号分隔、映射 `本地:IP:远端`、`all`、`exit-node` |
| 跨机查公开行用 `local` 当机名 | 机名用注册标签(如 lan-ubuntu);无参 view 是本机活动面 |
| 关映射只删状态档忘了地址已随进程作废 | close 即杀进程清四件,旧 addr 再连即拒 |

## 接着读

- `../agents/SKILL.md`:id 文法与知会信封,知会被拒时
