---
patterns: [房间, fleet, 大厅, 私信, dm, 在场, presence, 回执, ack, 播报, 社交]
---

## agents 协作惯例指导(IM 映射)

- 房间 = 流名 `room/` 前缀(deferred 代记、force-audit 审计、pipe-live 跨机管道、port-live 跨机端口映射);全舰队大厅 = `fleet` 流(`streams room fleet <消息>` 说,裸尾读取)
- 私信专线 `dm/<机:别名>/<机:别名>`(无名端退化 `机:格`);`streams dm <别名>` 与 `agents to` 自动镜像,流名与写法无关,避免双开劈叉
- 礼仪:一行一事带端名前缀(append 自动加 `<host>|`,勿手写裸追加);append-only 不撤回,更正 = 追加新行注明;大内容走 shares 上键流里放键引用;频道不做请求应答
- 批次完工回执:`streams append fleet "<批次、改面要点、去向>"`;在场列看 `agents view`,声明键 share/presence(勿扰带 until)
