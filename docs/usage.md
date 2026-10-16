# herdr-mesh 使用指南

部署完成后(docker/garage/s2/tailscale/herdr 面见 deploy.md),日常操作走
八条命令:`agents`(消息/工作台)、`shares`(文件)、`streams`(流/房间/私信)、
`tasks`(持久任务)、`pipes`(实时字节管道)、`ports`(端口转发映射)、
`ctxs`(对话历史检索)、`mcps`(MCP 目标:任意 MCP server 的 view/tools/call)。

## 命令安装(uv)

```bash
uv tool install --force git+https://github.com/raystyle/herdr-mesh#subdirectory=src
```

装出入口:`agents`、`shares`、`streams` 等八命令(各带 `--llms` 手册面)。

## 三段式文法(三命令同构)

```
<命令> [view [参数]]               # VIEW:全局可视,裸调用即 view,退出码 0
<命令> <OPERATE 动词> [参数...]     # OPERATE:只操作不扰人
<命令> to <目标> <资源...> [--force] # DELIVER:定向投递(过门控,投信封)
```

- 全局旗标任意槽:`--help -h --llms --json --format --full-output --filter-output --schema`;`--` 逃生口
- 退出码:0 成功;1 业务未命中/拒投;2 用法错

## 目标 id 文法

| 形 | 义 | 例 |
| --- | --- | --- |
| 裸名 | 全局按 agent 名搜(本机先,后各在册机) | `agents to alice "看下构建"` |
| `机:名或格` | 显式跨机;首冒号前 = 机标签 | `agents read node-a:w8:p1` |
| `local:格` | 本机显式形 | `agents keys local:w8:p1 Enter` |

裸 pane id 非法;无名格必须显式形。

## agents:消息与工作台

```bash
agents view                    # 全局格表(本机+远机,含在场状态)
agents machines                # 在网机器表
agents read alice --lines 40   # 读屏(自带忙候,--timeout 调)
agents to alice "评审请求已递"  # 投递消息(原子化:写入且目标开吃才算 delivered)
agents keys alice Enter        # 给格按键
agents start bob --kind claude # 起格跑 agent(命名见下)
agents ws myws                 # 开工作台(多格布局)
agents reload alice            # 翻台重载(同格同 session 重进,重载技能)
agents close alice             # 关格(优雅退,零击杀)
```

## shares:文件交换(S3 内容哈希键)

```bash
shares view                    # share/ 前缀键表
shares put report.md           # 上架(键 = share/<机>/<hash>/<文件名>)
shares get share/node-a/abc/report.md -o report.md   # 取回
shares to alice report.md      # 上架 + 给 alice 投信封(含取用命令)
```

## streams:持久流(S2,流即房间)

```bash
streams view                   # 流列表
streams view room/build --from 0 -n 20    # 读流(记游标)
streams append room/build "v1.2.3 已发"   # 追加(host 前缀自动带)
streams to alice room/build "请回执"      # 写流 + 给 alice 投信封
```

惯例:`room/<名>` = 房间广播;`dm/<a>/<b>` = 双人专线;`room/deferred/<格>` =
拒投代记流(补收看这里)。

## 投递语义(三命令一致)

- 投递动词统一 `to`;链路 = 门控(读目标 TUI 尾窗判操作对话框,有对话框即拒)
  -> 原子化写入(`--wait` 等目标开吃,15s 窗)
- status 四态:`delivered` 开吃 / `engine_fail` 引擎败 / `deferred` 拒投已代记 /
  `stalled` 写入未开吃
- `--force` 跳门控强投(慎用);拒投不丢件,自动落 `room/deferred/<格>`

## 消息信封(DELIVER 落到对方屏幕的形)

```
[shares] @alice 给你共享了文件「report.md」
from=node-a:w2:p1 to=alice key=share/node-a/xx/report.md name=report.md v=1
取用:s5 get -o report.md share/node-a/xx/report.md
```

三行形:人话行(自由)/ 字段行(逐字稳定,机器可解析)/ 取用行(禁改写)。

## 命名标准

agent 名 = `<工作台标签>-<类型>-<编号>`,如 `myws-claude-1`;编号即窗格位
(田字顺时针,满四开 tab)。存量名兼容。
