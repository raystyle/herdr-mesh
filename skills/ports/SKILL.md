---
name: ports
description: >-
  暴露本机口用 open,访问对方已开的口用 fwd;close 停映射。
  Use when: expose a port, port-forward, 端口转发、映射服务口。
  不要用于文件或消息。
---

# ports - evo 端口域原语

| 动词 | 文法 | 何时用 |
| --- | --- | --- |
| view | `view [host]` | 要看本机活动映射;带机 = 跨机公开行(room/port-live,机名用注册标签) |
| open | `open <spec>` | 要起端口转发(常驻至 close);spec = `8080,8443` 端口表 / `5555:IP:5555` 服务侧映射(serve 面被服务端口) / `all` / `exit-node` |
| close | `close <addr\|pid>` | 要关映射,地址作废 |
| fwd | `fwd <addr> <本地>:<远端口>` | 要本地起听转发接入映射(recipient 侧动词;0 = 空口,Ctrl+C 停) |
| to | `to <id> <spec> [--force]` | 要开映射并知会对方接入(取用行 ports fwd) |

## 文法

- 裸调用 = view;全局旗标以 `ports --llms` 为准
- 与 pipes 分野:pipes = 临时字节管道(本机收对方发);本域 = TCP 端口转发映射(tailcat serve,对方 forward 接入)
- 取用行 = `ports fwd <addr> <本地>:<远端口>`(引擎名退出取用行):数字 spec 全端口枚举,all/exit-node 出指引形;addr 在字段行
- 映射常驻至 close,无超时自关(`--keep` 已废,rc=2 拒)
- 状态目录 `~/.local/state/ports`(pid/addr/log/spec 四件);跨机公开流 room/port-live(不含地址)
- 消息走 agents;共享规则见 `../agents/SKILL.md`

## 示例

```bash
ports view node-a
ports open 8123
ports open 5555:10.2.200.213:5555
ports to repo-claude-1 8123
```

## 坑

| 错 | 对 |
| --- | --- |
| spec 敲成 URL 或带协议形 | 裸形:端口表逗号分隔、映射 `本地:IP:远端`、`all`、`exit-node` |
| 跨机查公开行用 `local` 当机名 | 机名用注册标签(如 node-a);无参 view 是本机活动面 |
| 敲 `open --keep` 求长驻 | 常驻即缺省,`--keep` rc=2 拒;关走 close(杀进程清四件,旧 addr 再连即拒) |
| win 首用直连被拦 | win 防火墙默认入站 Block;命令自带 CTA 放行提醒,规则名 tailcat-in(仅 DERP 中继可达即此因) |

## 接着读

- `../agents/SKILL.md`:id 文法与知会信封,知会被拒时
