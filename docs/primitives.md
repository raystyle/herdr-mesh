# 六原语速查

文法: `<命令> [全局旗标] <动词> [动词旗标] [位置参数...]`;裸调用 = view,退出码 0;全局七旗标 `--help -h --llms --json --format --full-output --filter-output --schema`;`--` 逃生口;未知词 usage 退 2。

| 命令 | VIEW | OPERATE | DELIVER(to) |
| --- | --- | --- | --- |
| agents | `view [机]`,`machines`,`list [机]` | `read <id> [--lines N] [--timeout S]`,`keys <id> <键...>`,`mode <dnd|away|online> [until]`,`start <名> --kind <类> [--pane 格] [-- AGENT_ARGS...]`,`ws <label> [--cwd DIR]`,`ws list [机]`,`ws close <台>`,`shell <机> <仓>`,`dev <机> <仓> [--kind]`,`split <id> [--direction]`,`tab <list|create|close>`,`zoom <id>`,`close <id>`,`reload <id>`,`wt [机] [--title 名]`,`trust`,`sync` | `to <id> <文本> [--force]` |
| shares | `view` | `put <文件>`,`get <键> [--output 名]` | `to <id> <文件> [--force]` |
| streams | `view [流] [-n N] [--from seq] [--resume]` | `append <流> <消息>` | `to <id> <流> <消息> [--force]` |
| tasks | `view [机]`(实时任务面) | `set <id> <文本>` | `to <id> <文本> [--force]` |
| pipes | `view [机]` | `open [--keep]`,`close <addr|pid>` | `to <id> [--force]` |
| ctx | `view [agent] [--limit N]`(gw_logs.head 最近请求头行) | `show <request_id>`(头行加正文块),`search <关键词> [--limit N]`(跨请求全文) | 无(检索域不投递) |

保留: room/ 与 dm/ 14 天,tasks/shared 30 天;fleet 流 = 全舰队回执主频道。ctx 窗口:head 365 天,正文块 180 天。

坑表(高频):

| 坑 | 正解 |
| --- | --- |
| 裸格直写格 id | 首冒号先当机标签;无名格必须 local:格 或 机:格 |
| 目标 working 不敢投 | 门控只拒对话框,busy 排队不拦 |
| 跨调用 ref 过期 | 页面换代全体作废;单片段内续用 |
| reload 非标准名被改名 | 存量名保名,仅非法字符修正并披露 |
| 引擎离线挂死整面 | herdr 容错 rc=124,view 跳过告警 |
| 方言写页面逻辑 | 方言管 CDP 编排,--js 管页面逻辑 |
