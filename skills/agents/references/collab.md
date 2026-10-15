# 协作惯例与 IM 映射

> 七原语之上的舰队社交层:房间、私信、在场、回执、回放。命名即路由,流即载体。

## IM 映射表

| IM 概念 | 协议形 | 说明 |
| --- | --- | --- |
| 聊天室/房间 | 流名带 `room/` 前缀 | room/deferred(代记)、room/force-audit(审计)、room/pipe-live(跨机管道)、room/port-live(跨机端口映射,契约面) |
| 全舰队大厅 | `fleet` 流 | 播报与回执主频道;`streams room fleet <消息>` 说房,`streams room fleet` 读房 |
| @某人 | DELIVER | 门控加信封加提示词落格;比房间消息重,要人看见才用 |
| 私信 | `dm/<a>/<b>` 流 | 双方名专线;`streams dm <对方别名>`,流名按双别名排序自动定,避免双开 |
| 在场状态 | `agents view` | presence 展示列;契约面另有声明键 share/presence(勿扰等,带 until) |
| 离线消息 | room/deferred | 拒投代记,收方补收(落点两形见 deliver-gate.md) |

## 消息礼仪

- 一行一事,带端名前缀(`streams append` 自动加 `<host>|`;勿手写引擎裸追加)
- append-only:发出去不撤回不改写;更正 = 追加新行注明更正对象
- 大内容走 shares 上键,流里只放键引用;频道不做请求应答(轮次协议不在 skill 面,持久任务域走 tasks 原语)
- 取阅 = `streams room` 或 `streams view`,不回写、不 re-put

## 回执与 ack 惯例

- 批次完工回执:`streams append fleet "<一句话:批次、改面要点、去向>"`;总台 tail 取阅
- ack:收到要紧件(交付、周知)回执到来源流或 dm,一行确认;文件件可回执 ack 键(shares 上 share/<名>/…-ack.txt 判例)
- 停机与阻塞:持久任务域走 tasks;消息域回执说明原因,不静默消失

## 回放与续读

- `streams view <流> --from <seq>`:从序号回放;全量 = `--from 0`
- `--resume`:从机内 cursor 续读(cursor 落 `~/.local/state/prim/cursor/<流名>`,机内不共享;换机从 0 或显式 seq 起)
- 默认尾读最近 100 行;要更多用 `-n N` 调量或 `--from` 回放
- 斜杠流名 cursor 崩已修(R1:父链全建,`view room/deferred/<格>` 净退 0);cursor 随每次具名 view 落盘,回放判据不受影响
- 保留策略(契约面):room/ 与 dm/ 14 天;tasks/shared 事件流已弃(tasks 域转实时任务面,旧档只读留档);要长留的内容上 shares 看板

## 与邻面分工

- 五域投递原语 skill = shares/streams/tasks/pipes/ports 各自持域面,ctxs 持历史检索面;本 skill(agents)持消息域与共享面(id、门控、信封、命名标准、差异表)
- 易混场景速判(A 族):「谁在跑」= agents view(在场)或 tasks view(任务文本),房间流回放不算;「实时」= pipes(字节)或 streams `-f`(消息),别混;「知会」要人立刻看见 = agents to,留痕给人翻 = streams,要对方记住 = tasks to
- s5 与 herdr 与 hst = 引擎(herdr 已退役出操作面);代理操作一律七原语,引擎裸面不再设 skill
- skill 面禁用原始 s5 裸命令(s5 put/s5 cat 等):文件一律 shares、流一律 streams,宿主前缀与引擎细节不进示例
- 取用行 = 回信命令:`agents to <裸别名> reply`(streams 域附 `(stream <流> attached)`)。取文件是 `shares get <键>`,键在字段行,不占 use 行;tasks 取用 = `tasks view`,pipes 取用 = `pipes send <addr>`,ports 取用 = `ports fwd <addr> <本地>:<远端口>`(数字 spec 全端口枚举)。收方照行执行即可
