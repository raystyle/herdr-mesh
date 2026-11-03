# herdr-mesh 使用指南

部署完成后(docker/garage/s2/tailscale/herdr 面见 deploy.md),日常操作走
十条命令:`agents`(消息/事件回信)、`machines`(机册:舰队节点管理)、
`desks`(工位/窗台拓扑操作)、`shares`(文件)、`streams`(流/房间/私信)、
`tasks`(持久任务)、`pipes`(实时字节管道)、`ports`(端口转发映射)、
`ctxs`(对话历史检索)、`mcps`(MCP 目标:任意 MCP server 的 view/tools/call)。

命名三分(ADR-0007):消息面 = agents,拓扑面 = desks(工位/窗格 = pane,
工作台/窗台 = workspace),机册面 = machines;`desk` 为旧名单字别名。

## 命令安装(uv)

```bash
uv tool install --force git+https://github.com/raystyle/herdr-mesh#subdirectory=src
```

装出入口:`agents`、`machines`、`desks`、`shares`、`streams` 等十命令(各带 `--llms` 手册面)。

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

## agents:消息与事件回信

```bash
agents view                    # 全局格表(本机+远机,含在场状态)
agents read alice --lines 40   # 读屏(自带忙候,--timeout 调)
agents to alice "评审请求已递"  # 投递消息(原子化:写入且目标开吃才算 delivered;同时镜像进 dm 流)
agents wait --from alice       # 阻塞等回信(信封到即返,agent 不再盲等)
agents inbox                   # 非阻塞收件单(dm 流入站消息清单)
agents keys alice Enter        # 给格按键
agents mode dnd 2h             # 在场自声明(勿勿扰两小时)
```

回信事件道:to 投递即镜像 dm 对流;wait 引擎级轮询到新入站信封即返全文。

## machines:机册(舰队节点)

```bash
machines view                  # 册表 + 可达性
machines add user@10.0.0.7 --label node-b   # 注册(herdr 自动装远端起 server)
machines disable node-b        # 下线禁用(view 不再扫)
machines runtime check         # 运行时环境(骑 ark;--machine 跨机)
machines run node-a w8:p1 "make test"       # 节点格内跑命令(pane 直透)
```

## desks:工位/窗台拓扑

```bash
desks                          # 拓扑视图:窗台->tab->工位分组,▍ 焦点工位
desks start bob --kind claude  # 起工位跑 agent(命名见下)
desks ws myws                  # 开工作台(多格布局,田字顺时针,满四开 tab)
desks split alice --direction right        # 邻格分屏
desks close alice              # 关工位(优雅退,零击杀)
desks reload alice             # 翻台重载(同格同 session 重进,重载技能)
desks yolo                     # 四家 CLI 权限面检测/冷翻
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
use: shares get share/node-a/xx/report.md -o report.md
```

四行形:头行(人话)/ 字段行(逐字稳定,机器可解析)/ `use:` 取用行(禁改写,全原语命令面)。

## 命名标准

agent 名 = `<工作台标签>-<类型>-<编号>`,如 `myws-claude-1`;编号 = 出生序号
(该台该类型从 1 起不复用,不等于当前格位);新名禁下划线只留连字符;
起名全局扫撞名拒绝;台名至多 22 字。存量名兼容不强制改。
